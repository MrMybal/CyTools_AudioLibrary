---
id: operation-add-folder
title: add_folder
description: Référencez un autre dossier audio (récursif). Exécutez scanlibrary ensuite.
section: Référence
order: 200
parent: operations
sourceRevision: 1a0d51b2f1b4a15e
---

Référencez un autre dossier audio (récursif). Exécutez scan_library ensuite.

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `libraryId` | `string` | Oui | Id de la Bibliothèque retourné par create_library ou list_libraries `pattern="^[0-9a-f]{8}$"` |
| `path` | `string` | Oui | Dossier audio. Chemin absolu sur l'ordinateur exécutant le Tool.  |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation add_folder
```
