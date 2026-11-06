---
id: operation-install-engine
title: install_engine
description: Create the private PyTorch environment at its final path and fetch the pinned engine sources. Long: several GB.
section: Reference
order: 200
parent: operations
revision: 6bbe92fb36e899bd
---

Create the private PyTorch environment at its final path and fetch the pinned engine sources. Long: several GB.

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `cpuOnly` | `boolean` | No | See the operation parameters. `default=false` |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation install_engine
```
