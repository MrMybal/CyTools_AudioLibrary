---
id: operation-library-status
title: library_status
description: Global figures: files, metadata %, waveforms %, one line per model, stores kept from previous versions, queue state.
section: Reference
order: 200
parent: operations
revision: 0052f0eea2d15c20
---

Global figures: files, metadata %, waveforms %, one line per model, stores kept from previous versions, queue state.

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `libraryId` | `string` | Yes | LibraryId returned by create_library or list_libraries `pattern="^[0-9a-f]{8}$"` |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation library_status
```
