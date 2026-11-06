---
id: operation-update-assets
title: update_assets
description: Données utilisateur (étiquettes, catégories, note, préféré, description, notes) d’un actif, d’une sélection (audioIds) ou de chaque actif correspondant à un filtre, par exemple un dossier : filtres {"rootIds": [rootId],…
section: Référence
order: 200
parent: operations
sourceRevision: fc50601da1b33209
---

Données utilisateur (étiquettes, catégories, note, préféré, description, notes) d’un actif, d’une sélection (audioIds) ou de chaque actif correspondant à un filtre, par exemple un dossier : filtres {"rootIds": [rootId], "folderPrefix": "Impacts/Metal"}. Seulement la base de données de la Bibliothèque change ; les fichiers audio ne sont jamais écrits ici. Les étiquettes et catégories automatiques sont stockées séparément et ne sont jamais surécrites par cette opération, ni les données utilisateur par une analyse redondante.

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `libraryId` | `string` | Oui | Id de la Bibliothèque retourné par create_library ou list_libraries `pattern="^[0-9a-f]{8}$"` |
| `audioIds` | `array` | Non | Voir les paramètres de l’opération.  |
| `filters` | `object` | Non | Tous les actifs correspondant à ces filtres sont édités également (même filtres que pour browse_assets). Ne doit pas être vide.  |
| `setTags` | `array` | Non | Remplacer les étiquettes utilisateur  |
| `addTags` | `array` | Non | Voir les paramètres de l’opération.  |
| `removeTags` | `array` | Non | Voir les paramètres de l’opération.  |
| `setCategories` | `array` | Non | Remplacer les catégories utilisateur (ids de catégories)  |
| `addCategories` | `array` | Non | Ajouter des catégories utilisateur (ids de catégories), en conservant les autres  |
| `removeCategories` | `array` | Non | Supprimer ces catégories utilisateur (ids de catégories)  |
| `favorite` | `boolean` | Non | Voir les paramètres de l’opération.  |
| `rating` | `integer` | Non | Voir les paramètres de l’opération. `minimum=0`, `maximum=5` |
| `description` | `string` | Non | Voir les paramètres de l’opération.  |
| `notes` | `string` | Non | Remplacer les notes  |
| `appendNotes` | `string` | Non | Ajoutez cette ligne après les notes existantes de chaque cible, sans les remplacer  |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation update_assets
```
