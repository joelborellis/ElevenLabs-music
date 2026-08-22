# Claude Code Prompt: Generate MCP Server Specification (Node.js)

> Feed this prompt to Claude Code from within the FastAPI (Keepsong) project. It will analyze the codebase and produce a specification document you can use to build a Node.js/TypeScript MCP server in a separate project.

---

You are analyzing a FastAPI backend application (Keepsong) to create a detailed specification for converting it into a native MCP (Model Context Protocol) server built with Node.js/TypeScript.

## Your Task

Read through the entire FastAPI codebase and generate a comprehensive specification document that describes:

1. **Pipeline Architecture** - Document the four-stage pipeline:
   - Plan: composition planning logic and inputs/outputs
   - Prompt: music prompt generation logic and inputs/outputs
   - Render: audio rendering logic, both HTTP and WebSocket paths
   - Finetune: finetune discovery and sound profile logic

2. **Data Models** - For each stage, document:
   - Input data structures (what the client sends)
   - Output data structures (what the server returns)
   - Any intermediate models or transformations
   - Database models if applicable
   - NOTE: These will be translated to TypeScript interfaces/types

3. **Service Logic** - Document the business logic in the services layer:
   - plan_generator.py logic and dependencies
   - prompt_generator.py logic and dependencies
   - render_service.py logic (HTTP and WebSocket handling)
   - finetune_service.py logic and the finetune discovery flow
   - NOTE: This logic will need to be reimplemented in TypeScript

4. **ElevenLabs Integration** - Document:
   - How the FastAPI backend currently integrates with ElevenLabs API
   - API calls made, parameters passed, responses handled
   - Error handling and retries
   - NOTE: Identify which Node.js libraries can handle this (axios, node-fetch, etc.)

5. **Storage & Persistence** - Document:
   - Database schema and SQLAlchemy models
   - Storage layer (blob storage integration)
   - How data flows through the system
   - NOTE: Consider which Node.js ORMs/database libraries will be used

6. **Authentication & Authorization Requirements** - Document:
   - Current security posture (note: currently "wide open")
   - Where OAuth/Entra ID validation will be needed in the MCP server
   - What credentials/tokens need to be passed through
   - NOTE: The Node.js MCP server will validate Entra ID tokens from Teams/Agent 365

7. **MCP Server Tool Mapping** - For each endpoint/route, define:
   - Tool name (e.g., "create_composition_plan")
   - Tool description
   - Input parameters and types
   - Output structure
   - Any special handling (WebSocket vs HTTP, long-running jobs, etc.)
   - NOTE: These will become MCP tool definitions in the Node.js server

8. **Configuration & Environment** - Document:
   - Environment variables used
   - Configuration values from config.py
   - ElevenLabs API key handling
   - Database connection strings
   - NOTE: How these will be managed in a Node.js environment

9. **Testing Strategy** - Reference what's in the testing/ folder:
   - Existing test cases that should inform the MCP implementation
   - Mock data (like finetunes.json) that will be useful
   - NOTE: Tests will be written in Jest or similar Node.js test framework

10. **Implementation Notes** - Provide guidance on:
    - Which parts are straightforward to convert to TypeScript
    - Which parts have complexity that needs careful handling
    - Any gotchas or edge cases to watch for in the Node.js version
    - Suggested Node.js libraries/packages for each major component

## Output Format

Create a structured markdown document with clear sections, code examples where helpful, and a summary diagram showing the tool flow. The spec should be detailed enough that a Node.js/TypeScript developer can build the MCP server from scratch without needing to reference the FastAPI code again.

## Files to Analyze

Start by examining:
- main.py (entry point and route definitions)
- routers/ (all endpoint definitions)
- services/ (business logic)
- models/ (data structures)
- db/ (database models)
- config.py (configuration)
- Testing files to understand expected behavior

## Important Context

This specification will be used to build a Node.js/TypeScript MCP server that:
- Runs alongside a React frontend (also Node.js/TypeScript ecosystem)
- Authenticates users via Entra ID when deployed in Teams or Agent 365
- Exposes the Keepsong pipeline (plan → prompt → render → finetune) as MCP tools
- Handles both standard and WebSocket-based rendering operations

Begin your analysis now and generate the complete specification.
