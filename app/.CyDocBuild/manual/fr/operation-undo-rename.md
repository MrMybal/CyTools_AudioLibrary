---
id: operation-undo-rename
title: undo_rename
description: CHANGES ORIGINAL FILES. Restaure les noms de la dernière batch de renommage qui n'a pas été annulée encore.
section: Référence
order: 200
parent: operations
sourceRevision: 757c5629ac74852c
---

CHANGES ORIGINAL FILES. Restaure les noms de la dernière batch de renommage qui n'a pas été annulée encore.

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `libraryId` | `string` | Oui | Id de la Bibliothèque retourné par create_library ou list_libraries `pattern="^[0-9a-f]{8}$"` |
| `confirm` | `boolean` | Oui | Doit être vrai. Cette opération change les fichiers originaux de l'utilisateur : un client AI doit montrer le plan à l'utilisateur et obtenir une confirmation explicite d'un oui.  |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation undo_rename
```
