# HTTP Middleware Documentation

This document explains the HTTP middleware used in the FastAPI application, specifically the `@app.middleware("http")` decorator and its implementation.

## Overview

The application uses FastAPI's HTTP middleware to intercept and process every incoming HTTP request before it reaches the route handlers, and to modify responses before they are sent back to clients.

## Request ID Middleware

### Implementation

```python
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID to each request for tracing."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    return response
```

### How It Works

1. **Intercept Incoming Request**: Every HTTP request that arrives at the application passes through this middleware first.

2. **Extract or Generate Request ID**: 
   - The middleware checks if the incoming request already has an `X-Request-ID` header
   - If present, it uses that existing ID (useful for distributed tracing across services)
   - If not present, it generates a new UUID v4 as the request ID

3. **Store on Request State**: The request ID is stored on `request.state.request_id`, making it accessible to all route handlers and other middleware throughout the request lifecycle.

4. **Call Next Handler**: `await call_next(request)` passes the request to the next middleware or the actual route handler.

5. **Add to Response**: Before returning the response, the middleware adds the `X-Request-ID` header to the response, allowing clients to reference this ID.

## Why This Middleware Is Used

### 1. **Distributed Tracing**
Request IDs enable tracking a single request as it flows through multiple services in a microservices architecture. When a request spans multiple services, the same ID can be passed along, creating a traceable chain.

### 2. **Debugging and Support**
When users report issues, they can provide the `X-Request-ID` from the response headers. Support teams can then search logs using this ID to find exactly what happened during that request.

### 3. **Log Correlation**
All log entries related to a single request can include the request ID, making it easy to filter and analyze logs for specific requests:
```python
logger.error(
    "Validation error",
    extra={
        "request_id": request_id,
        "path": request.url.path,
        "errors": exc.errors()
    }
)
```

### 4. **Error Responses**
The application includes the request ID in error responses, helping users and developers identify specific failed requests:
```python
return JSONResponse(
    content=ErrorResponse(
        error="Internal Server Error",
        message="An unexpected error occurred. Please contact support with the request ID.",
        request_id=request_id,
        timestamp=datetime.utcnow().isoformat()
    ).model_dump()
)
```

## Middleware Execution Order

Understanding middleware order is critical in FastAPI:

1. **Order of Definition Matters**: Middleware is executed in the order it's added to the application.

2. **CORS Middleware**: In this application, CORS middleware is added before the request ID middleware:
   ```python
   app.add_middleware(CORSMiddleware, ...)
   ```

3. **Request Flow**: 
   ```
   Client Request
        ↓
   CORS Middleware (handles preflight, adds CORS headers)
        ↓
   Request ID Middleware (adds X-Request-ID)
        ↓
   FastAPI Route Handler
        ↓
   Request ID Middleware (adds X-Request-ID to response)
        ↓
   CORS Middleware (ensures CORS headers on response)
        ↓
   Client Response
   ```

## Key Considerations

### Thread Safety
The `request.state` object is request-scoped, meaning each request gets its own isolated state. This prevents request ID collisions in concurrent environments.

### Performance
Generating a UUID and adding headers has minimal overhead. The middleware is asynchronous (`async def`), so it doesn't block the event loop.

### Client-Provided Request IDs
The middleware accepts client-provided `X-Request-ID` headers. This is intentional for:
- Allowing upstream services to propagate their trace IDs
- Enabling clients to pre-generate IDs for their own tracking

**Security Note**: If you need to prevent clients from setting their own request IDs (for audit purposes), modify the middleware to always generate a new ID:
```python
request_id = str(uuid.uuid4())  # Always generate, ignore client header
```

### Exposed Headers
The CORS configuration exposes `X-Request-ID` so browsers can access it:
```python
app.add_middleware(
    CORSMiddleware,
    ...
    expose_headers=["X-Request-ID"],
)
```

Without this, JavaScript in browsers cannot read the `X-Request-ID` header from responses.

## Integration with OpenTelemetry

This middleware complements the OpenTelemetry instrumentation in the application:

- **OpenTelemetry** provides distributed tracing with span IDs and trace IDs
- **Request ID Middleware** provides a human-readable, application-level identifier

Both work together to provide comprehensive observability. The request ID can be correlated with OpenTelemetry traces for complete request visibility.

## Usage in Route Handlers

Route handlers can access the request ID through the request object:

```python
@app.get("/example")
async def example_endpoint(request: Request):
    request_id = getattr(request.state, "request_id", "unknown")
    # Use request_id for logging, tracing, etc.
    return {"request_id": request_id}
```

## Best Practices

1. **Always log the request ID** in any error or significant event logging
2. **Include in API responses** when returning detailed information
3. **Pass to downstream services** when making HTTP calls to other services
4. **Store in database records** for audit trails when creating/modifying data
