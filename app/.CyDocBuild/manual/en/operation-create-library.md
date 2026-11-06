---
id: operation-create-library
title: create_library
description: Create a virtual Library. Folders are referenced, never copied or modified. The cache can live on any drive.
section: Reference
order: 200
parent: operations
revision: cd6e90f538f9011b
---

Create a virtual Library. Folders are referenced, never copied or modified. The cache can live on any drive.

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `name` | `string` | Yes | See the operation parameters.  |
| `cacheLocation` | `string` | No | Absolute folder for all derived data (database, waveforms, embeddings). Empty = data/cache of the Tool.  |
| `folders` | `array` | No | Absolute audio folders to add immediately  |
| `enableDefaultModels` | `boolean` | No | Enable the installed default embedding models `default=true` |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation create_library
```
