---
id: operation-search-sounds
title: search_sounds
description: Find sounds in the user's local audio Libraries from a free-text description in any language (or sounds similar to a known asset). Omit libraryId to search every Library at once. Each result gives the absolute path of the…
section: Reference
order: 200
parent: operations
revision: 8796cabf33a129c3
---

Find sounds in the user's local audio Libraries from a free-text description in any language (or sounds similar to a known asset). Omit libraryId to search every Library at once. Each result gives the absolute path of the original file, duration, tags, categories, a 0-100 score per model and, for long recordings, the matching time segment: enough to propose sounds to the user. Each model retrieves from its own index; ranks are fused with weighted Reciprocal Rank Fusion. The job is asynchronous: poll cy_get_job and read outputs.results when Completed.

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `libraryId` | `string` | No | Optional. Absent = search all Libraries (results carry libraryId and libraryName). Required with similarTo. `pattern="^[0-9a-f]{8}$"` |
| `text` | `string` | No | Free text in any language, e.g. "gros impact métallique très lourd avec une longue réverbération"  |
| `similarTo` | `string` | No | Find sounds similar to this asset (its stored embedding is the query) `pattern="^[0-9a-f]{32}$"` |
| `selectionStart` | `number` | No | With similarTo: start of the time selection used as the audio query, seconds `minimum=0` |
| `selectionEnd` | `number` | No | With similarTo: end of the time selection, seconds `minimum=0` |
| `models` | `array` | No | Embedding models to use. Empty or absent = every model enabled for the Library. Each model retrieves independently.  |
| `filters` | `object` | No | Classic filters, combined with AND. They also restrict a semantic search.  |
| `topK` | `integer` | No | See the operation parameters. `default=50`, `minimum=1`, `maximum=2000` |
| `llmAssist` | `string` | No | Small local LLM for query understanding. auto = only for long, non-English, negated or sequential requests. `default="auto"`, `enum=["off", "auto", "always"]` |
| `llmModel` | `string` | No | modelKey of the LLM; empty = the model chosen in the application settings, which is what the interface uses too `default=""` |
| `weights` | `object` | No | Rank-fusion weight per modelKey for this search  |
| `rrfK` | `integer` | No | K of Reciprocal Rank Fusion `default=60`, `minimum=1`, `maximum=1000` |
| `device` | `string` | No | auto = CUDA GPU when the engine sees one, else CPU. gpu fails when CUDA is unavailable. cpu reserves RAM only. `default="auto"`, `enum=["auto", "gpu", "cpu"]` |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation search_sounds
```
