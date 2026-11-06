---
id: operation-get-asset
title: get_asset
description: Metadata, levels, user and automatic tags/categories with the model that produced them, captions and per-model analysis states.
section: Reference
order: 200
parent: operations
revision: 2ee820c84bfc87d3
---

Metadata, levels, user and automatic tags/categories with the model that produced them, captions and per-model analysis states.

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `libraryId` | `string` | Yes | LibraryId returned by create_library or list_libraries `pattern="^[0-9a-f]{8}$"` |
| `audioId` | `string` | Yes | Stable AudioId of an asset (survives renames and moves) `pattern="^[0-9a-f]{32}$"` |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation get_asset
```
