---
id: operation-release-models
title: release_models
description: Décharger tous les modèles et arrêter le worker d'engine maintenant (libère RAM/VRAM). Refusé pendant qu'une analyse ou une recherche est en cours.
section: Référence
order: 200
parent: operations
sourceRevision: 232fe3113e767a68
---

Décharger tous les modèles et arrêter le worker d'engine maintenant (libère RAM/VRAM). Refusé pendant qu'une analyse ou une recherche est en cours.

## Paramètres {#contract}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation release_models
```
