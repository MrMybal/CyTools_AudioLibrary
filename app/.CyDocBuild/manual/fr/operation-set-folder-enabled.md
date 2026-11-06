---
id: operation-set-folder-enabled
title: set_folder_enabled
description: Un dossier désactivé est sauté par les scans et masqué de la navigation ; rien n'est supprimé.
section: Référence
order: 200
parent: operations
sourceRevision: 6e9a03a3cbba94df
---

Un dossier désactivé est sauté par les scans et masqué de la navigation ; rien n'est supprimé.

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `libraryId` | `string` | Oui | Id de la Bibliothèque retourné par create_library ou list_libraries `pattern="^[0-9a-f]{8}$"` |
| `rootId` | `string` | Oui | Voir les paramètres de l’opération.  |
| `enabled` | `boolean` | Oui | Voir les paramètres de l’opération.  |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation set_folder_enabled
```
