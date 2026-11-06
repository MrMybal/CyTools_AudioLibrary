---
id: operation-control-analysis
title: control_analysis
description: Pause or resume the analysis queue of a Library (shared by the UI, CLI and MCP). Use canceljob to cancel it.
section: Reference
order: 200
parent: operations
revision: a3c7d953106becc8
---

Pause or resume the analysis queue of a Library (shared by the UI, CLI and MCP). Use cancel_job to cancel it.

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `libraryId` | `string` | Yes | LibraryId returned by create_library or list_libraries `pattern="^[0-9a-f]{8}$"` |
| `action` | `string` | Yes | See the operation parameters. `enum=["pause", "resume"]` |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation control_analysis
```
