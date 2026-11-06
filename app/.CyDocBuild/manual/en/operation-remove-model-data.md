---
id: operation-remove-model-data
title: remove_model_data
description: Delete one embedding store (analysis key) of a Library, e.g. the data of a previous model version. Other models and versions are untouched.
section: Reference
order: 200
parent: operations
revision: 8eb6b0418b07b1dd
---

Delete one embedding store (analysis key) of a Library, e.g. the data of a previous model version. Other models and versions are untouched.

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `libraryId` | `string` | Yes | LibraryId returned by create_library or list_libraries `pattern="^[0-9a-f]{8}$"` |
| `analysisKey` | `string` | Yes | See the operation parameters. `pattern="^[0-9a-f]{16}$"` |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation remove_model_data
```
