---
id: operation-install-engine
title: install_engine
description: Créer l'environnement privé PyTorch à son chemin final et récupérer les sources d'engine fixées. Long: plusieurs GB.
section: Référence
order: 200
parent: operations
sourceRevision: 6bbe92fb36e899bd
---

Créer l'environnement privé PyTorch à son chemin final et récupérer les sources d'engine fixées. Long: plusieurs GB.

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `cpuOnly` | `boolean` | Non | Voir les paramètres de l’opération. `default=false` |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation install_engine
```
