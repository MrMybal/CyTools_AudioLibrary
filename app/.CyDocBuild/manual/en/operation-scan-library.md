---
id: operation-scan-library
title: scan_library
description: Incremental recursive scan: new, unchanged, modified, moved, missing and duplicate files, then metadata, loudness and waveform cache for new/modified files only.
section: Reference
order: 200
parent: operations
revision: 1da7770ca16fcf14
---

Incremental recursive scan: new, unchanged, modified, moved, missing and duplicate files, then metadata, loudness and waveform cache for new/modified files only.

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `libraryId` | `string` | Yes | LibraryId returned by create_library or list_libraries `pattern="^[0-9a-f]{8}$"` |
| `rootIds` | `array` | No | Rescan only these folders  |
| `analyzeCommon` | `boolean` | No | Also compute metadata + waveform for pending files `default=true` |
| `retryFailed` | `boolean` | No | See the operation parameters. `default=false` |
| `threads` | `integer` | No | See the operation parameters. `minimum=1`, `maximum=32` |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation scan_library
```
