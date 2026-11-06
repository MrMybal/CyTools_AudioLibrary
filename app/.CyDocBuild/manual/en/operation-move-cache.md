---
id: operation-move-cache
title: move_cache
description: Copy the whole cache of a Library to another location, verify it, then switch. The previous copy is kept.
section: Reference
order: 200
parent: operations
revision: b63dd2fd7ab776ef
---

Copy the whole cache of a Library to another location, verify it, then switch. The previous copy is kept.

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `libraryId` | `string` | Yes | LibraryId returned by create_library or list_libraries `pattern="^[0-9a-f]{8}$"` |
| `cacheLocation` | `string` | Yes | New cache root. Absolute path on the machine running the Tool.  |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation move_cache
```
