---
id: operation-purge-missing
title: purge_missing
description: Delete the database rows and analysis of assets whose file is missing. Explicit; original files are not concerned.
section: Reference
order: 200
parent: operations
revision: 6727dcebf0644d50
---

Delete the database rows and analysis of assets whose file is missing. Explicit; original files are not concerned.

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `libraryId` | `string` | Yes | LibraryId returned by create_library or list_libraries `pattern="^[0-9a-f]{8}$"` |
| `confirm` | `boolean` | Yes | See the operation parameters.  |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation purge_missing
```
