---
id: operation-undo-rename
title: undo_rename
description: CHANGES ORIGINAL FILES. Restores the names of the most recent rename batch that was not undone yet.
section: Reference
order: 200
parent: operations
revision: 757c5629ac74852c
---

CHANGES ORIGINAL FILES. Restores the names of the most recent rename batch that was not undone yet.

## Parameters {#contract}

| Name | Type | Required | Description |
|---|---|---|---|
| `libraryId` | `string` | Yes | LibraryId returned by create_library or list_libraries `pattern="^[0-9a-f]{8}$"` |
| `confirm` | `boolean` | Yes | Must be true. This operation changes the user's original files: an AI client must show the plan to the user and obtain an explicit yes first.  |
## Returns {#returns}

No named fields are declared at this level. Inspect the operation schema with `describe-operation` for its exact shape.

## Behaviour and access {#behaviour}

- Required permissions: none declared.
- Backends: none declared.
- Cancellation: supported.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation undo_rename
```
