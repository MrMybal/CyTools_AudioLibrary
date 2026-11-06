---
id: operation-get-waveform
title: get_waveform
description: Min/max peaks of a time range from the cached pyramid (no decoding).
section: Reference
order: 200
parent: operations
revision: ab88efe07901d924
---

Min/max peaks of a time range from the cached pyramid (no decoding).

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `libraryId` | `string` | Yes | LibraryId returned by create_library or list_libraries `pattern="^[0-9a-f]{8}$"` |
| `audioId` | `string` | Yes | Stable AudioId of an asset (survives renames and moves) `pattern="^[0-9a-f]{32}$"` |
| `start` | `number` | No | Seconds `default=0`, `minimum=0` |
| `stop` | `number` | No | Seconds; absent = end of file `minimum=0` |
| `columns` | `integer` | No | See the operation parameters. `default=1024`, `minimum=16`, `maximum=8192` |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation get_waveform
```
