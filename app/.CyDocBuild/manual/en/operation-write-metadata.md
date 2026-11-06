---
id: operation-write-metadata
title: write_metadata
description: CHANGES ORIGINAL FILES. Writes description, tags, categories, rating and AudioId into the files themselves (ID3 for WAV/AIFF/MP3, Vorbis comments for FLAC/OGG/Opus, MP4 atoms for M4A). Tags are written into a copy, the decoded…
section: Reference
order: 200
parent: operations
revision: f2e9a9f98f18c285
---

CHANGES ORIGINAL FILES. Writes description, tags, categories, rating and AudioId into the files themselves (ID3 for WAV/AIFF/MP3, Vorbis comments for FLAC/OGG/Opus, MP4 atoms for M4A). Tags are written into a copy, the decoded audio is verified identical, then the copy replaces the original; a backup goes to the Library cache by default. Embeddings stay valid.

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `libraryId` | `string` | Yes | LibraryId returned by create_library or list_libraries `pattern="^[0-9a-f]{8}$"` |
| `audioIds` | `array` | Yes | See the operation parameters.  |
| `fields` | `array` | No | Absent = all  |
| `includeAutoTags` | `boolean` | No | false = user tags only `default=true` |
| `backup` | `boolean` | No | Keep the untouched original in <cache>/Common/FileOperations/Backups `default=true` |
| `confirm` | `boolean` | Yes | Must be true. This operation changes the user's original files: an AI client must show the plan to the user and obtain an explicit yes first.  |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation write_metadata
```
