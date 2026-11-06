---
id: operation-check-library
title: check_library
description: Read-only and fast: compares the folders with the database (size and date only) and reports new, modified, missing and restored files, without writing anything. Call scanlibrary when changed is true.
section: Reference
order: 200
parent: operations
revision: ca355549640a9dca
---

Read-only and fast: compares the folders with the database (size and date only) and reports new, modified, missing and restored files, without writing anything. Call scan_library when changed is true.

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `libraryId` | `string` | Yes | LibraryId returned by create_library or list_libraries `pattern="^[0-9a-f]{8}$"` |
| `rootIds` | `array` | No | Check only these folders  |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation check_library
```
