---
id: operation-categorize-library
title: categorize_library
description: Recompute les catégories et balises automatiques à partir des embeddings stockés avec la taxonomie actuelle. Pas de décodage audio ; les balises des utilisateurs restent inchangées.
section: Référence
order: 200
parent: operations
sourceRevision: c62b23ab658fccce
---

Recompute les catégories et balises automatiques à partir des embeddings stockés avec la taxonomie actuelle. Pas de décodage audio ; les balises des utilisateurs restent inchangées.

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `libraryId` | `string` | Oui | Id de la Bibliothèque retourné par create_library ou list_libraries `pattern="^[0-9a-f]{8}$"` |
| `models` | `array` | Non | Modèles d'embedding à utiliser. Vide ou absent = tous les modèles actifs pour la Bibliothèque. Chaque modèle récupère indépendamment.  |
| `device` | `string` | Non | auto = CUDA GPU lorsque le moteur voit un, sinon CPU. gpu échoue lorsque CUDA est indisponible. cpu réserve RAM uniquement. `default="auto"`, `enum=["auto", "gpu", "cpu"]` |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation categorize_library
```
