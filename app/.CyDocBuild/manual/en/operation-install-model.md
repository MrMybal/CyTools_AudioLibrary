---
id: operation-install-model
title: install_model
description: Download (with resume), verify and register a catalogue model. Licences that require it must be accepted personally with acceptLicense=true. Credentials are never parameters.
section: Reference
order: 200
parent: operations
revision: 8b3ec59d14786907
---

Download (with resume), verify and register a catalogue model. Licences that require it must be accepted personally with acceptLicense=true. Credentials are never parameters.

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `modelKey` | `string` | Yes | modelId@version from list_models `pattern="^[A-Za-z][A-Za-z0-9_.-]{0,63}@[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$"` |
| `acceptLicense` | `boolean` | No | Your own acceptance of the model licence shown by list_models `default=false` |
| `repair` | `boolean` | No | Re-hash every file and download corrupted ones again `default=false` |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation install_model
```
