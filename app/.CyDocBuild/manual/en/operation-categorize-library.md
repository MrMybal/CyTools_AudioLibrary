---
id: operation-categorize-library
title: categorize_library
description: Recompute automatic categories and tags from stored embeddings with the current taxonomy. No audio decoding; user tags untouched.
section: Reference
order: 200
parent: operations
revision: c62b23ab658fccce
---

Recompute automatic categories and tags from stored embeddings with the current taxonomy. No audio decoding; user tags untouched.

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `libraryId` | `string` | Yes | LibraryId returned by create_library or list_libraries `pattern="^[0-9a-f]{8}$"` |
| `models` | `array` | No | Embedding models to use. Empty or absent = every model enabled for the Library. Each model retrieves independently.  |
| `device` | `string` | No | auto = CUDA GPU when the engine sees one, else CPU. gpu fails when CUDA is unavailable. cpu reserves RAM only. `default="auto"`, `enum=["auto", "gpu", "cpu"]` |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation categorize_library
```
