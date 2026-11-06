---
id: operation-browse-assets
title: browse_assets
description: Une page d’actifs avec des filtres et des tri classiques (virtuels : seulement la fenêtre demandée est materialisée).
section: Référence
order: 200
parent: operations
sourceRevision: 7a497caee6ba753d
---

Une page d’actifs avec des filtres et des tri classiques (virtuels : seulement la fenêtre demandée est materialisée).

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `libraryId` | `string` | Oui | Id de la Bibliothèque retourné par create_library ou list_libraries `pattern="^[0-9a-f]{8}$"` |
| `filters` | `object` | Non | Filtres classiques combinés avec AND. Ils restreignent également une recherche sémantique.  |
| `sort` | `string` | Non | category = première catégorie affichée (celles des utilisateurs en premier), par nom ; tags = première étiquette affichée ; state = échecs, en attente, puis prêts. `default="name"`, `enum=["name", "duration", "type", "folder", "size", "modified", "added", "rating", "played", "sampleRate", "channels", "category", "tags", "state"]` |
| `descending` | `boolean` | Non | Voir les paramètres de l’opération. `default=false` |
| `offset` | `integer` | Non | Voir les paramètres de l’opération. `default=0`, `minimum=0` |
| `limit` | `integer` | Non | Voir les paramètres de l’opération. `default=100`, `minimum=1`, `maximum=1000` |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation browse_assets
```
