---
id: operation-remove-model
title: remove_model
description: Uninstall the weights of a catalogue model, or unregister a custom model (its files are never deleted). Analysis data of each Library is kept unless deleteAnalysis is true.
section: Reference
order: 200
parent: operations
revision: bd50d6ece55e4cf5
---

Uninstall the weights of a catalogue model, or unregister a custom model (its files are never deleted). Analysis data of each Library is kept unless deleteAnalysis is true.

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `modelKey` | `string` | Yes | modelId@version from list_models `pattern="^[A-Za-z][A-Za-z0-9_.-]{0,63}@[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$"` |
| `deleteAnalysis` | `boolean` | No | Also delete the embeddings/indexes of this model in every Library `default=false` |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation remove_model
```
