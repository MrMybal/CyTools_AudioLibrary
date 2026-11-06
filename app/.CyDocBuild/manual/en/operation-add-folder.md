---
id: operation-add-folder
title: add_folder
description: Reference one more audio folder (recursive). Run scanlibrary afterwards.
section: Reference
order: 200
parent: operations
revision: 1a0d51b2f1b4a15e
---

Reference one more audio folder (recursive). Run scan_library afterwards.

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `libraryId` | `string` | Yes | LibraryId returned by create_library or list_libraries `pattern="^[0-9a-f]{8}$"` |
| `path` | `string` | Yes | Audio folder. Absolute path on the machine running the Tool.  |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation add_folder
```
