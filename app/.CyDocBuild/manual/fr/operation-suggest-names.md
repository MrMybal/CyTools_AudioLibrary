---
id: operation-suggest-names
title: suggest_names
description: Lecture seule. Suggère des noms descriptifs (catégorie + tags) pour des fichiers mal nommés comme sound01.wav ou ZOOM0012..wav. Retourne un plan ; rien n'est renommé.
section: Référence
order: 200
parent: operations
sourceRevision: f1156c7762823bd6
---

Lecture seule. Suggère des noms descriptifs (catégorie + tags) pour des fichiers mal nommés comme sound_01.wav ou ZOOM0012..wav. Retourne un plan ; rien n'est renommé.

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `libraryId` | `string` | Oui | Id de la Bibliothèque retourné par create_library ou list_libraries `pattern="^[0-9a-f]{8}$"` |
| `audioIds` | `array` | Non | Absent = toute la Bibliothèque  |
| `onlyBadlyNamed` | `boolean` | Non | false = propose un nom pour chaque fichier listé `default=true` |
| `template` | `string` | Non | Champs : {category} {tags} {original} {duration} `default="{category}_{tags}"` |
| `maxTags` | `integer` | Non | Voir les paramètres de l’opération. `default=3`, `minimum=0`, `maximum=8` |
| `limit` | `integer` | Non | Voir les paramètres de l’opération. `default=500`, `minimum=1`, `maximum=5000` |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation suggest_names
```
