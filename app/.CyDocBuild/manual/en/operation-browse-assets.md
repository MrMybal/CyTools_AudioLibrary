---
id: operation-browse-assets
title: browse_assets
description: One page of assets with classic filters and sorting (virtualised: only the requested window is materialised).
section: Reference
order: 200
parent: operations
revision: 7a497caee6ba753d
---

One page of assets with classic filters and sorting (virtualised: only the requested window is materialised).

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `libraryId` | `string` | Yes | LibraryId returned by create_library or list_libraries `pattern="^[0-9a-f]{8}$"` |
| `filters` | `object` | No | Classic filters, combined with AND. They also restrict a semantic search.  |
| `sort` | `string` | No | category = first category shown (user ones first), by name; tags = first tag shown; state = failed, pending, then ready. `default="name"`, `enum=["name", "duration", "type", "folder", "size", "modified", "added", "rating", "played", "sampleRate", "channels", "category", "tags", "state"]` |
| `descending` | `boolean` | No | See the operation parameters. `default=false` |
| `offset` | `integer` | No | See the operation parameters. `default=0`, `minimum=0` |
| `limit` | `integer` | No | See the operation parameters. `default=100`, `minimum=1`, `maximum=1000` |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation browse_assets
```
