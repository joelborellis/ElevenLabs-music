# Timeout Fix for Usage Examples

## Problem
The `usage_examples.py` script was throwing `httpx.ReadTimeout` errors when trying to generate prompts:

```
httpcore.ReadTimeout
```

## Root Cause
The OpenAI API calls made by the Agents SDK can take 30-60 seconds to complete. The default `httpx` timeout is only 5 seconds, causing requests to time out before the prompt is generated.

## Solution
Updated all `httpx.AsyncClient` instances to use a 60-second timeout:

```python
# Before
async with httpx.AsyncClient() as client:

# After  
async with httpx.AsyncClient(timeout=60.0) as client:
```

## Files Updated
1. `examples/usage_examples.py` - All 7 client instances updated
2. `testing/test_prompt_endpoint.py` - Both client instances updated

## Additional Improvements
Added user-friendly messages to indicate processing time:

```python
print("\nGenerating prompt (this may take 30-60 seconds)...")
print("\nNote: Each request may take 30-60 seconds due to OpenAI API processing time.")
```

## Verification
Test the fix with:

```bash
# Start the server in one terminal
uv run python main.py

# In another terminal, run the examples
uv run python examples/usage_examples.py
```

Expected behavior:
- ✅ Requests complete successfully after 30-60 seconds
- ✅ No timeout errors
- ✅ Prompts are generated and displayed

## Why 60 Seconds?
- OpenAI GPT models can take 20-40 seconds for complex prompts
- Network latency adds 2-5 seconds
- 60 seconds provides a comfortable buffer
- Most requests complete in 30-40 seconds

## Alternative: Increase Further if Needed
If you still experience timeouts, you can increase further:

```python
async with httpx.AsyncClient(timeout=120.0) as client:  # 2 minutes
```

Or set different timeouts for different operations:

```python
timeout = httpx.Timeout(
    connect=10.0,   # Connection timeout
    read=90.0,      # Read timeout (most important for long AI calls)
    write=10.0,     # Write timeout
    pool=10.0       # Pool timeout
)
async with httpx.AsyncClient(timeout=timeout) as client:
```
