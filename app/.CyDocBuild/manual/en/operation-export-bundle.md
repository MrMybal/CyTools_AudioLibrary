---
id: operation-export-bundle
title: export_bundle
description: Copy a selection of sounds (audioIds) or every sound a filter matches into a folder the user chooses, for instance to prepare what a game engine or a DAW will import. The originals are only read. Nothing is ever overwritten: a…
section: Reference
order: 200
parent: operations
revision: e0debcbbae2ff916
---

Copy a selection of sounds (audioIds) or every sound a filter matches into a folder the user chooses, for instance to prepare what a game engine or a DAW will import. The originals are only read. Nothing is ever overwritten: a file already present with the same content is left as it is, a different one with the same name gets a numbered name. A destination that would put copies inside a folder of any Library or inside a cache is refused. bundle.json lists every file with its source, AudioId, duration, tags and categories; exporting into the same folder again adds to it.

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `libraryId` | `string` | Yes | LibraryId returned by create_library or list_libraries `pattern="^[0-9a-f]{8}$"` |
| `audioIds` | `array` | No | See the operation parameters.  |
| `filters` | `object` | No | Every asset these filters match is copied too (same filters as browse_assets). Must not be empty.  |
| `destination` | `string` | Yes | Absolute folder path; created if it does not exist  |
| `layout` | `string` | No | flat = every file directly in the destination; folders = <root folder name>/<sub folders>/<file> `default="flat"`, `enum=["flat", "folders"]` |
| `manifest` | `boolean` | No | Write or update bundle.json in the destination `default=true` |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation export_bundle
```
