---
id: operation-get-waveform
title: get_waveform
description: Pic min/max d’un intervalle de temps depuis la pyramide tamisée (pas de décodage).
section: Référence
order: 200
parent: operations
sourceRevision: ab88efe07901d924
---

Pic min/max d’un intervalle de temps depuis la pyramide tamisée (pas de décodage).

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `libraryId` | `string` | Oui | Id de la Bibliothèque retourné par create_library ou list_libraries `pattern="^[0-9a-f]{8}$"` |
| `audioId` | `string` | Oui | AudioId stable d’un actif (survient les renoms et déplacements) `pattern="^[0-9a-f]{32}$"` |
| `start` | `number` | Non | Secondes `default=0`, `minimum=0` |
| `stop` | `number` | Non | Secondes ; absent = fin de fichier `minimum=0` |
| `columns` | `integer` | Non | Voir les paramètres de l’opération. `default=1024`, `minimum=16`, `maximum=8192` |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation get_waveform
```
