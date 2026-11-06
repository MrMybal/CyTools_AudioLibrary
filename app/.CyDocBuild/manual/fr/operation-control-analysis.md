---
id: operation-control-analysis
title: control_analysis
description: Pauzez ou reprenez la file d'attente d'analyse d'une bibliothèque (partagée par le UI, CLI et MCP). Utilisez canceljob pour l'annuler.
section: Référence
order: 200
parent: operations
sourceRevision: a3c7d953106becc8
---

Pauzez ou reprenez la file d'attente d'analyse d'une bibliothèque (partagée par le UI, CLI et MCP). Utilisez cancel_job pour l'annuler.

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `libraryId` | `string` | Oui | Id de la Bibliothèque retourné par create_library ou list_libraries `pattern="^[0-9a-f]{8}$"` |
| `action` | `string` | Oui | Voir les paramètres de l’opération. `enum=["pause", "resume"]` |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation control_analysis
```
