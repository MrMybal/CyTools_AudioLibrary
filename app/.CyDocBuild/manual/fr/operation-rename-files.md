---
id: operation-rename-files
title: rename_files
description: CHANGES ORIGINAL FILES. Renomme les fichiers sur le disque dans leur dossier (jamais d'écriture sur place, l'extension est conservée). AudioId, tags, waveform et embeddings suivent le fichier. Journalisé : undorename annule la…
section: Référence
order: 200
parent: operations
sourceRevision: 6f715186ebf854de
---

CHANGES ORIGINAL FILES. Renomme les fichiers sur le disque dans leur dossier (jamais d'écriture sur place, l'extension est conservée). AudioId, tags, waveform et embeddings suivent le fichier. Journalisé : undo_rename annule la dernière batch.

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `libraryId` | `string` | Oui | Id de la Bibliothèque retourné par create_library ou list_libraries `pattern="^[0-9a-f]{8}$"` |
| `renames` | `array` | Oui | Voir les paramètres de l’opération.  |
| `confirm` | `boolean` | Oui | Doit être vrai. Cette opération change les fichiers originaux de l'utilisateur : un client AI doit montrer le plan à l'utilisateur et obtenir une confirmation explicite d'un oui.  |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation rename_files
```
