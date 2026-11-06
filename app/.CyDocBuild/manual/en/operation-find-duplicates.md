---
id: operation-find-duplicates
title: find_duplicates
description: Group exact duplicates (size + hash, confirmed by SHA-256) or probable duplicates (embedding similarity + duration). Reports and groups only: nothing is deleted.
section: Reference
order: 200
parent: operations
revision: c4a414c0d6bd0af5
---

Group exact duplicates (size + hash, confirmed by SHA-256) or probable duplicates (embedding similarity + duration). Reports and groups only: nothing is deleted.

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `libraryId` | `string` | Yes | LibraryId returned by create_library or list_libraries `pattern="^[0-9a-f]{8}$"` |
| `mode` | `string` | No | See the operation parameters. `default="exact"`, `enum=["exact", "probable"]` |
| `model` | `string` | No | modelId@version from list_models `pattern="^[A-Za-z][A-Za-z0-9_.-]{0,63}@[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$"` |
| `threshold` | `number` | No | Cosine similarity for probable duplicates `default=0.985`, `minimum=0.8`, `maximum=1.0` |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation find_duplicates
```
