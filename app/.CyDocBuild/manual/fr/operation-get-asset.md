---
id: operation-get-asset
title: get_asset
description: Métadonnées, niveaux, étiquettes et catégories utilisateurs et automatiques avec le modèle qui les a produites, légendes et états d’analyse par modèle.
section: Référence
order: 200
parent: operations
sourceRevision: 2ee820c84bfc87d3
---

Métadonnées, niveaux, étiquettes et catégories utilisateurs et automatiques avec le modèle qui les a produites, légendes et états d’analyse par modèle.

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `libraryId` | `string` | Oui | Id de la Bibliothèque retourné par create_library ou list_libraries `pattern="^[0-9a-f]{8}$"` |
| `audioId` | `string` | Oui | AudioId stable d’un actif (survient les renoms et déplacements) `pattern="^[0-9a-f]{32}$"` |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation get_asset
```
