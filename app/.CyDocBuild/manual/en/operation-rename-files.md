---
id: operation-rename-files
title: rename_files
description: CHANGES ORIGINAL FILES. Renames files on disk inside their folder (never overwrites, extension kept). AudioId, tags, waveform and embeddings follow the file. Journalled: undorename reverses the last batch.
section: Reference
order: 200
parent: operations
revision: 6f715186ebf854de
---

CHANGES ORIGINAL FILES. Renames files on disk inside their folder (never overwrites, extension kept). AudioId, tags, waveform and embeddings follow the file. Journalled: undo_rename reverses the last batch.

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `libraryId` | `string` | Yes | LibraryId returned by create_library or list_libraries `pattern="^[0-9a-f]{8}$"` |
| `renames` | `array` | Yes | See the operation parameters.  |
| `confirm` | `boolean` | Yes | Must be true. This operation changes the user's original files: an AI client must show the plan to the user and obtain an explicit yes first.  |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation rename_files
```
