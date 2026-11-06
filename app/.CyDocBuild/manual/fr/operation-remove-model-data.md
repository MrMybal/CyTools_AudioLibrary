---
id: operation-remove-model-data
title: remove_model_data
description: Supprimer une base d'embeddings (clé d'analyse) d'une Bibliothèque, par exemple les données d'une version précédente du modèle. Les autres modèles et versions ne sont pas touchés.
section: Référence
order: 200
parent: operations
sourceRevision: 8eb6b0418b07b1dd
---

Supprimer une base d'embeddings (clé d'analyse) d'une Bibliothèque, par exemple les données d'une version précédente du modèle. Les autres modèles et versions ne sont pas touchés.

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `libraryId` | `string` | Oui | Id de la Bibliothèque retourné par create_library ou list_libraries `pattern="^[0-9a-f]{8}$"` |
| `analysisKey` | `string` | Oui | Voir les paramètres de l’opération. `pattern="^[0-9a-f]{16}$"` |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation remove_model_data
```
