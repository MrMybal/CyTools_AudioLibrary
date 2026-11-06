---
id: operation-list-folders
title: list_folders
description: Folder structure of a Library as its audio files describe it: every folder with its recursive and direct file counts, per root folder. Use a path from here as filters.folderPrefix (with rootIds) in browseassets, updateassets,…
section: Reference
order: 200
parent: operations
revision: 99054175cb9489d2
---

Folder structure of a Library as its audio files describe it: every folder with its recursive and direct file counts, per root folder. Use a path from here as filters.folderPrefix (with rootIds) in browse_assets, update_assets, or to collect audioIds for analyze_library, suggest_names and write_metadata.

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `libraryId` | `string` | Yes | LibraryId returned by create_library or list_libraries `pattern="^[0-9a-f]{8}$"` |
| `rootId` | `string` | No | Only this root folder  |
| `folderPrefix` | `string` | No | Start below this folder, relative to the root, '/' separated  |
| `maxDepth` | `integer` | No | Levels below the start; 0 = all `default=2`, `minimum=0`, `maximum=64` |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation list_folders
```
