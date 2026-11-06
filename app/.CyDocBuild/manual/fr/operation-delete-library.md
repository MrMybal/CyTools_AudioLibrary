---
id: operation-delete-library
title: delete_library
description: Oublier une Bibliothèque. Les fichiers audio ne sont jamais touchés ; le cache est effacé uniquement sur demande.
section: Référence
order: 200
parent: operations
sourceRevision: 86116ff0375b340b
---

Oublier une Bibliothèque. Les fichiers audio ne sont jamais touchés ; le cache est effacé uniquement sur demande.

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `libraryId` | `string` | Oui | Id de la Bibliothèque retourné par create_library ou list_libraries `pattern="^[0-9a-f]{8}$"` |
| `deleteCache` | `boolean` | Non | Voir les paramètres de l’opération. `default=false` |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation delete_library
```
