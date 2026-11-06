---
id: operation-remove-folder
title: remove_folder
description: Arrêtez de référencer un dossier. Ses actifs deviennent manquants et conservent leur analyse jusqu'à purgemissing.
section: Référence
order: 200
parent: operations
sourceRevision: f549297b51ddcbda
---

Arrêtez de référencer un dossier. Ses actifs deviennent manquants et conservent leur analyse jusqu'à purge_missing.

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `libraryId` | `string` | Oui | Id de la Bibliothèque retourné par create_library ou list_libraries `pattern="^[0-9a-f]{8}$"` |
| `rootId` | `string` | Oui | Voir les paramètres de l’opération.  |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation remove_folder
```
