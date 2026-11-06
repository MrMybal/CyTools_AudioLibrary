---
id: operation-set-folder-enabled
title: set_folder_enabled
description: A disabled folder is skipped by scans and hidden from browsing; nothing is deleted.
section: Reference
order: 200
parent: operations
revision: 6e9a03a3cbba94df
---

A disabled folder is skipped by scans and hidden from browsing; nothing is deleted.

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `libraryId` | `string` | Yes | LibraryId returned by create_library or list_libraries `pattern="^[0-9a-f]{8}$"` |
| `rootId` | `string` | Yes | See the operation parameters.  |
| `enabled` | `boolean` | Yes | See the operation parameters.  |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation set_folder_enabled
```
