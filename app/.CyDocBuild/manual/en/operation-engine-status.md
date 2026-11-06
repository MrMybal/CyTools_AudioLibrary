---
id: operation-engine-status
title: engine_status
description: State of the private AI engine environment, its pinned sources and the models currently loaded in the worker.
section: Reference
order: 200
parent: operations
revision: 0511894cd78ff04d
---

State of the private AI engine environment, its pinned sources and the models currently loaded in the worker.

## Parameters {#contract}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation engine_status
```
