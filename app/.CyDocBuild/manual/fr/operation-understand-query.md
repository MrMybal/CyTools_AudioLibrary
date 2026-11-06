---
id: operation-understand-query
title: understand_query
description: Transforme une requête libre en une requête structurée stable (événements, propriétés, environnement, exclure, temporel, requêtes) sans effectuer de recherche.
section: Référence
order: 200
parent: operations
sourceRevision: 632e158df4dc674f
---

Transforme une requête libre en une requête structurée stable (événements, propriétés, environnement, exclure, temporel, requêtes) sans effectuer de recherche.

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `text` | `string` | Oui | Voir les paramètres de l’opération.  |
| `llmAssist` | `string` | Non | Voir les paramètres de l’opération. `default="always"`, `enum=["off", "auto", "always"]` |
| `llmModel` | `string` | Non | Voir les paramètres de l’opération. `default=""` |
| `device` | `string` | Non | auto = CUDA GPU lorsque le moteur voit un, sinon CPU. gpu échoue lorsque CUDA est indisponible. cpu réserve RAM uniquement. `default="auto"`, `enum=["auto", "gpu", "cpu"]` |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation understand_query
```
