---
id: operation-delete-library
title: delete_library
description: Forget a Library. Audio files are never touched; the cache is deleted only on request.
section: Reference
order: 200
parent: operations
revision: 86116ff0375b340b
---

Forget a Library. Audio files are never touched; the cache is deleted only on request.

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `libraryId` | `string` | Yes | LibraryId returned by create_library or list_libraries `pattern="^[0-9a-f]{8}$"` |
| `deleteCache` | `boolean` | No | See the operation parameters. `default=false` |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation delete_library
```
