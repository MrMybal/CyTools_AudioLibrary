---
id: operation-update-library
title: update_library
description: Renommer une Bibliothèque, modifier ses paramètres, ses modèles actifs ou sa taxonomie.
section: Référence
order: 200
parent: operations
sourceRevision: 92add326916dcc89
---

Renommer une Bibliothèque, modifier ses paramètres, ses modèles actifs ou sa taxonomie.

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `libraryId` | `string` | Oui | Id de la Bibliothèque retourné par create_library ou list_libraries `pattern="^[0-9a-f]{8}$"` |
| `name` | `string` | Non | Voir les paramètres de l’opération.  |
| `settings` | `object` | Non | Paramètres de la Bibliothèque. Modifier la segmentation crée une nouvelle clé d'analyse : les embeddings précédents sont conservés.  |
| `enabledModels` | `array` | Non | Modèles d'embedding à utiliser. Vide ou absent = tous les modèles actifs pour la Bibliothèque. Chaque modèle récupère indépendamment.  |
| `taxonomy` | `object` | Non | Voir les paramètres de l’opération.  |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation update_library
```
