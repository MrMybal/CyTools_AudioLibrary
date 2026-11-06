---
id: operation-list-folders
title: list_folders
description: Structure de dossier d'une Library telle que ses fichiers audio la décrivent : chaque dossier avec ses comptes de fichiers récursifs et directs, par dossier racine. Utilisez un chemin de là pour filtrer avec…
section: Référence
order: 200
parent: operations
sourceRevision: 99054175cb9489d2
---

Structure de dossier d'une Library telle que ses fichiers audio la décrivent : chaque dossier avec ses comptes de fichiers récursifs et directs, par dossier racine. Utilisez un chemin de là pour filtrer avec filters.folderPrefix (avec rootIds) dans browse_assets, update_assets, ou pour collecter audioIds pour analyze_library, suggest_names et write_metadata.

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `libraryId` | `string` | Oui | Id de la Bibliothèque retourné par create_library ou list_libraries `pattern="^[0-9a-f]{8}$"` |
| `rootId` | `string` | Non | Seulement ce dossier racine  |
| `folderPrefix` | `string` | Non | Commencez à partir de ce dossier, relativement à la racine, '/' séparé  |
| `maxDepth` | `integer` | Non | Niveaux en dessous du point de départ ; 0 = tous `default=2`, `minimum=0`, `maximum=64` |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation list_folders
```
