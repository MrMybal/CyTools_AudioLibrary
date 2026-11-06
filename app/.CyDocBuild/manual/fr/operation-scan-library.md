---
id: operation-scan-library
title: scan_library
description: Scan incrémental récursif : nouveaux, inchangés, modifiés, déplacés, manquants et duplicats, puis métadonnées, niveau de bruit et cache de la forme d'onde uniquement pour les nouveaux/modifyés.
section: Référence
order: 200
parent: operations
sourceRevision: 1da7770ca16fcf14
---

Scan incrémental récursif : nouveaux, inchangés, modifiés, déplacés, manquants et duplicats, puis métadonnées, niveau de bruit et cache de la forme d'onde uniquement pour les nouveaux/modifyés.

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `libraryId` | `string` | Oui | Id de la Bibliothèque retourné par create_library ou list_libraries `pattern="^[0-9a-f]{8}$"` |
| `rootIds` | `array` | Non | Rescannez uniquement ces dossiers  |
| `analyzeCommon` | `boolean` | Non | Calculez également les métadonnées et la forme d'onde pour les fichiers en attente `default=true` |
| `retryFailed` | `boolean` | Non | Voir les paramètres de l’opération. `default=false` |
| `threads` | `integer` | Non | Voir les paramètres de l’opération. `minimum=1`, `maximum=32` |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation scan_library
```
