---
id: operation-purge-missing
title: purge_missing
description: Supprime les lignes de la base de données et l'analyse des actifs dont le fichier est manquant. Explicite ; les fichiers originaux ne sont pas concernés.
section: Référence
order: 200
parent: operations
sourceRevision: 6727dcebf0644d50
---

Supprime les lignes de la base de données et l'analyse des actifs dont le fichier est manquant. Explicite ; les fichiers originaux ne sont pas concernés.

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `libraryId` | `string` | Oui | Id de la Bibliothèque retourné par create_library ou list_libraries `pattern="^[0-9a-f]{8}$"` |
| `confirm` | `boolean` | Oui | Voir les paramètres de l’opération.  |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation purge_missing
```
