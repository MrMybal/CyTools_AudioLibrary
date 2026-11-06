---
id: operation-update-library
title: update_library
description: Rename a Library, change its settings, its enabled models or its taxonomy.
section: Reference
order: 200
parent: operations
revision: 92add326916dcc89
---

Rename a Library, change its settings, its enabled models or its taxonomy.

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `libraryId` | `string` | Yes | LibraryId returned by create_library or list_libraries `pattern="^[0-9a-f]{8}$"` |
| `name` | `string` | No | See the operation parameters.  |
| `settings` | `object` | No | Library settings. Changing segmentation creates a new analysis key: previous embeddings are kept.  |
| `enabledModels` | `array` | No | Embedding models to use. Empty or absent = every model enabled for the Library. Each model retrieves independently.  |
| `taxonomy` | `object` | No | See the operation parameters.  |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation update_library
```
