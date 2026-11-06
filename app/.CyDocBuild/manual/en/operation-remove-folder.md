---
id: operation-remove-folder
title: remove_folder
description: Stop referencing a folder. Its assets become missing and keep their analysis until purgemissing.
section: Reference
order: 200
parent: operations
revision: f549297b51ddcbda
---

Stop referencing a folder. Its assets become missing and keep their analysis until purge_missing.

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `libraryId` | `string` | Yes | LibraryId returned by create_library or list_libraries `pattern="^[0-9a-f]{8}$"` |
| `rootId` | `string` | Yes | See the operation parameters.  |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation remove_folder
```
