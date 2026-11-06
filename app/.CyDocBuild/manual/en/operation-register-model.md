---
id: operation-register-model
title: register_model
description: Register a local model, a fine-tuned variant or another version, in place. Several versions of one modelId coexist; each keeps its own embeddings.
section: Reference
order: 200
parent: operations
revision: e07897d288bad0b4
---

Register a local model, a fine-tuned variant or another version, in place. Several versions of one modelId coexist; each keeps its own embeddings.

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `modelId` | `string` | Yes | See the operation parameters. `pattern="^[A-Za-z][A-Za-z0-9_.-]{0,63}$"` |
| `version` | `string` | Yes | See the operation parameters. `pattern="^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$"` |
| `displayName` | `string` | Yes | See the operation parameters.  |
| `modelType` | `string` | Yes | See the operation parameters. `enum=["AudioTextEmbedding", "AudioEmbedding", "LLM", "AudioUnderstanding"]` |
| `adapter` | `string` | Yes | m2d_clap | hf_clap | omni_embed | hf_causal_lm | file:<absolute adapter.py>  |
| `localPath` | `string` | Yes | Absolute folder or weight file; referenced in place, never copied  |
| `capabilities` | `array` | Yes | See the operation parameters.  |
| `embeddingDimension` | `integer` | No | See the operation parameters. `minimum=1`, `maximum=16384` |
| `requiredSampleRate` | `integer` | No | See the operation parameters. `minimum=8000`, `maximum=192000` |
| `maximumAudioDuration` | `number` | No | See the operation parameters. `minimum=0.1` |
| `preferredChunkDuration` | `number` | No | See the operation parameters. `minimum=0.5`, `maximum=600` |
| `revision` | `string` | No | See the operation parameters.  |
| `family` | `string` | No | See the operation parameters.  |
| `provider` | `string` | No | See the operation parameters.  |
| `repository` | `string` | No | See the operation parameters.  |
| `licenseName` | `string` | No | See the operation parameters.  |
| `licenseUrl` | `string` | No | See the operation parameters.  |
| `engine` | `string` | No | See the operation parameters. `default="torch"`, `enum=["torch", "base"]` |
| `similarityRange` | `array` | No | Cosine range mapped to 0..100 % for display  |
| `promptProfile` | `string` | No | Which prompt this model was trained for. "generic" is the built-in instruction with its few-shot examples; "caption" is the clap_prompt/variations/suggested_* schema. A model is never recognised by its name, it declares its profile here. `default="generic"`, `enum=["generic", "caption"]` |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation register_model
```
