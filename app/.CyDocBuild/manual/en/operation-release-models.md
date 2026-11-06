---
id: operation-release-models
title: release_models
description: Unload every model and stop the engine worker now (frees RAM/VRAM). Refused while an analysis or search is running.
section: Reference
order: 200
parent: operations
revision: 232fe3113e767a68
---

Unload every model and stop the engine worker now (frees RAM/VRAM). Refused while an analysis or search is running.

## Parameters {#contract}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation release_models
```
