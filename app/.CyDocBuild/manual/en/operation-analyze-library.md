---
id: operation-analyze-library
title: analyze_library
description: Compute the missing embeddings (whole clip + overlapping segments) for each selected model, then automatic categories and tags. Existing waveforms, metadata and other models' embeddings are never recomputed.
section: Reference
order: 200
parent: operations
revision: 6a545c94301d165d
---

Compute the missing embeddings (whole clip + overlapping segments) for each selected model, then automatic categories and tags. Existing waveforms, metadata and other models' embeddings are never recomputed.

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `libraryId` | `string` | Yes | LibraryId returned by create_library or list_libraries `pattern="^[0-9a-f]{8}$"` |
| `models` | `array` | No | Embedding models to use. Empty or absent = every model enabled for the Library. Each model retrieves independently.  |
| `retryFailed` | `boolean` | No | See the operation parameters. `default=false` |
| `device` | `string` | No | auto = CUDA GPU when the engine sees one, else CPU. gpu fails when CUDA is unavailable. cpu reserves RAM only. `default="auto"`, `enum=["auto", "gpu", "cpu"]` |
| `audioIds` | `array` | No | Restrict to these assets  |
| `autoLabel` | `boolean` | No | Categorize and tag newly analyzed files `default=true` |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation analyze_library
```
