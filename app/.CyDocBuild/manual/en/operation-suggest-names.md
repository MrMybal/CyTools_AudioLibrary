---
id: operation-suggest-names
title: suggest_names
description: Read-only. Proposes descriptive names (category + tags) for badly named files such as sound01.wav or ZOOM0012.wav. Returns a plan; nothing is renamed.
section: Reference
order: 200
parent: operations
revision: f1156c7762823bd6
---

Read-only. Proposes descriptive names (category + tags) for badly named files such as sound_01.wav or ZOOM0012.wav. Returns a plan; nothing is renamed.

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `libraryId` | `string` | Yes | LibraryId returned by create_library or list_libraries `pattern="^[0-9a-f]{8}$"` |
| `audioIds` | `array` | No | Absent = whole Library  |
| `onlyBadlyNamed` | `boolean` | No | false = propose a name for every listed file `default=true` |
| `template` | `string` | No | Fields: {category} {tags} {original} {duration} `default="{category}_{tags}"` |
| `maxTags` | `integer` | No | See the operation parameters. `default=3`, `minimum=0`, `maximum=8` |
| `limit` | `integer` | No | See the operation parameters. `default=500`, `minimum=1`, `maximum=5000` |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation suggest_names
```
