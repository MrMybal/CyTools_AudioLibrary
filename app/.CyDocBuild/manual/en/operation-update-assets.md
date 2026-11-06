---
id: operation-update-assets
title: update_assets
description: User data (tags, categories, rating, favourite, description, notes) of one asset, a selection (audioIds) or every asset a filter matches, for instance one folder: filters {"rootIds": [rootId], "folderPrefix": "Impacts/Metal"}.…
section: Reference
order: 200
parent: operations
revision: fc50601da1b33209
---

User data (tags, categories, rating, favourite, description, notes) of one asset, a selection (audioIds) or every asset a filter matches, for instance one folder: filters {"rootIds": [rootId], "folderPrefix": "Impacts/Metal"}. Only the Library database changes; audio files are never written here. Automatic tags and categories are stored apart and never overwritten by this operation, nor user data by a re-analysis.

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `libraryId` | `string` | Yes | LibraryId returned by create_library or list_libraries `pattern="^[0-9a-f]{8}$"` |
| `audioIds` | `array` | No | See the operation parameters.  |
| `filters` | `object` | No | Every asset these filters match is edited too (same filters as browse_assets). Must not be empty.  |
| `setTags` | `array` | No | Replace the user tags  |
| `addTags` | `array` | No | See the operation parameters.  |
| `removeTags` | `array` | No | See the operation parameters.  |
| `setCategories` | `array` | No | Replace the user categories (category ids)  |
| `addCategories` | `array` | No | Add user categories (category ids), keeping the others  |
| `removeCategories` | `array` | No | Remove these user categories (category ids)  |
| `favorite` | `boolean` | No | See the operation parameters.  |
| `rating` | `integer` | No | See the operation parameters. `minimum=0`, `maximum=5` |
| `description` | `string` | No | See the operation parameters.  |
| `notes` | `string` | No | Replace the notes  |
| `appendNotes` | `string` | No | Add this line after the existing notes of every target, never replacing them  |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation update_assets
```
