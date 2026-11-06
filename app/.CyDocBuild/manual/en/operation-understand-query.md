---
id: operation-understand-query
title: understand_query
description: Turn a free-form request into the stable structured query (events, properties, environment, exclude, temporal, queries) without searching.
section: Reference
order: 200
parent: operations
revision: 632e158df4dc674f
---

Turn a free-form request into the stable structured query (events, properties, environment, exclude, temporal, queries) without searching.

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `text` | `string` | Yes | See the operation parameters.  |
| `llmAssist` | `string` | No | See the operation parameters. `default="always"`, `enum=["off", "auto", "always"]` |
| `llmModel` | `string` | No | See the operation parameters. `default=""` |
| `device` | `string` | No | auto = CUDA GPU when the engine sees one, else CPU. gpu fails when CUDA is unavailable. cpu reserves RAM only. `default="auto"`, `enum=["auto", "gpu", "cpu"]` |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation understand_query
```
