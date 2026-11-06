---
id: operation-write-metadata
title: write_metadata
description: CHANGES ORIGINAL FILES. Écrit la description, les balises, les catégories, l'évaluation et l'AudioId dans les fichiers eux-mêmes (ID3 pour WAV/AIFF/MP3, des commentaires Vorbis pour FLAC/OGG/Opus, des atomes MP4 pour M4A). Les…
section: Référence
order: 200
parent: operations
sourceRevision: f2e9a9f98f18c285
---

CHANGES ORIGINAL FILES. Écrit la description, les balises, les catégories, l'évaluation et l'AudioId dans les fichiers eux-mêmes (ID3 pour WAV/AIFF/MP3, des commentaires Vorbis pour FLAC/OGG/Opus, des atomes MP4 pour M4A). Les balises sont écrites dans une copie, l'audio décodé est vérifié identique, puis la copie remplace l'original ; une sauvegarde est par défaut stockée dans le cache de la bibliothèque. Les embeddings restent valides.

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `libraryId` | `string` | Oui | Id de la Bibliothèque retourné par create_library ou list_libraries `pattern="^[0-9a-f]{8}$"` |
| `audioIds` | `array` | Oui | Voir les paramètres de l’opération.  |
| `fields` | `array` | Non | Absent = tous  |
| `includeAutoTags` | `boolean` | Non | false = uniquement les balises des utilisateurs `default=true` |
| `backup` | `boolean` | Non | Gardez l'original non modifié dans <cache>/Common/FileOperations/Backups `default=true` |
| `confirm` | `boolean` | Oui | Doit être vrai. Cette opération change les fichiers originaux de l'utilisateur : un client AI doit montrer le plan à l'utilisateur et obtenir une confirmation explicite d'un oui.  |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation write_metadata
```
