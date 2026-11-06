---
id: operation-remove-model
title: remove_model
description: Désinstaller les poids d'un modèle du catalogue, ou désenregistrer un modèle personnalisé (ses fichiers ne sont jamais supprimés). Les données d'analyse de chaque Bibliothèque sont conservées sauf si deleteAnalysis est vrai.
section: Référence
order: 200
parent: operations
sourceRevision: bd50d6ece55e4cf5
---

Désinstaller les poids d'un modèle du catalogue, ou désenregistrer un modèle personnalisé (ses fichiers ne sont jamais supprimés). Les données d'analyse de chaque Bibliothèque sont conservées sauf si deleteAnalysis est vrai.

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `modelKey` | `string` | Oui | modelId@version de list_models `pattern="^[A-Za-z][A-Za-z0-9_.-]{0,63}@[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$"` |
| `deleteAnalysis` | `boolean` | Non | Supprimer également les embeddings/indexes de ce modèle dans chaque Bibliothèque `default=false` |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation remove_model
```
