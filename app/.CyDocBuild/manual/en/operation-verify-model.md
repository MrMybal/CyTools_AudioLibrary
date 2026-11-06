---
id: operation-verify-model
title: verify_model
description: Re-hash the installed files of a model against its receipt.
section: Reference
order: 200
parent: operations
revision: 5dfba763669fd9b5
---

Re-hash the installed files of a model against its receipt.

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `modelKey` | `string` | Yes | modelId@version from list_models `pattern="^[A-Za-z][A-Za-z0-9_.-]{0,63}@[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$"` |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation verify_model
```
