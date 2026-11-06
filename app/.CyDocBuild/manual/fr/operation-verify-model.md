---
id: operation-verify-model
title: verify_model
description: Re-hacher les fichiers installés d'un modèle contre sa facture.
section: Référence
order: 200
parent: operations
sourceRevision: 5dfba763669fd9b5
---

Re-hacher les fichiers installés d'un modèle contre sa facture.

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `modelKey` | `string` | Oui | modelId@version de list_models `pattern="^[A-Za-z][A-Za-z0-9_.-]{0,63}@[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$"` |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation verify_model
```
