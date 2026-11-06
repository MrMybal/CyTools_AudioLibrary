---
id: operation-check-library
title: check_library
description: Lecture seule et rapide : compare les dossiers avec la base de données (seulement la taille et la date) et rapporte les fichiers nouveaux, modifiés, manquants et restaurés, sans écrire quoi que ce soit. Appelez scanlibrary…
section: Référence
order: 200
parent: operations
sourceRevision: ca355549640a9dca
---

Lecture seule et rapide : compare les dossiers avec la base de données (seulement la taille et la date) et rapporte les fichiers nouveaux, modifiés, manquants et restaurés, sans écrire quoi que ce soit. Appelez scan_library lorsque changed est vrai.

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `libraryId` | `string` | Oui | Id de la Bibliothèque retourné par create_library ou list_libraries `pattern="^[0-9a-f]{8}$"` |
| `rootIds` | `array` | Non | Vérifiez uniquement ces dossiers  |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation check_library
```
