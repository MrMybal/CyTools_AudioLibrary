---
id: operation-move-cache
title: move_cache
description: Copiez l'ensemble du cache d'une Bibliothèque vers une autre emplacement, vérifiez-le, puis effectuez le changement. La copie précédente est conservée.
section: Référence
order: 200
parent: operations
sourceRevision: b63dd2fd7ab776ef
---

Copiez l'ensemble du cache d'une Bibliothèque vers une autre emplacement, vérifiez-le, puis effectuez le changement. La copie précédente est conservée.

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `libraryId` | `string` | Oui | Id de la Bibliothèque retourné par create_library ou list_libraries `pattern="^[0-9a-f]{8}$"` |
| `cacheLocation` | `string` | Oui | Nouveau racine du cache. Chemin absolu sur l'ordinateur exécutant le Tool.  |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation move_cache
```
