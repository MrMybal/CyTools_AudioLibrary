---
id: operation-library-status
title: library_status
description: Données globales : fichiers, pourcentage de métadonnées, pourcentage de formes d’onde, une ligne par modèle, stockages conservés des versions précédentes, état de la file d’attente.
section: Référence
order: 200
parent: operations
sourceRevision: 0052f0eea2d15c20
---

Données globales : fichiers, pourcentage de métadonnées, pourcentage de formes d’onde, une ligne par modèle, stockages conservés des versions précédentes, état de la file d’attente.

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `libraryId` | `string` | Oui | Id de la Bibliothèque retourné par create_library ou list_libraries `pattern="^[0-9a-f]{8}$"` |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation library_status
```
