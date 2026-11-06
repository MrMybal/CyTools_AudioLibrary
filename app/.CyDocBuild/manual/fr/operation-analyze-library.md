---
id: operation-analyze-library
title: analyze_library
description: Calculez les embeddings manquants (l'ensemble du clip + les segments superposés) pour chaque modèle sélectionné, puis les catégories et les tags automatiques. Les ondes d'onde, les métadonnées et les embeddings d'autres…
section: Référence
order: 200
parent: operations
sourceRevision: 6a545c94301d165d
---

Calculez les embeddings manquants (l'ensemble du clip + les segments superposés) pour chaque modèle sélectionné, puis les catégories et les tags automatiques. Les ondes d'onde, les métadonnées et les embeddings d'autres modèles ne sont jamais recalculés.

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `libraryId` | `string` | Oui | Id de la Bibliothèque retourné par create_library ou list_libraries `pattern="^[0-9a-f]{8}$"` |
| `models` | `array` | Non | Modèles d'embedding à utiliser. Vide ou absent = tous les modèles actifs pour la Bibliothèque. Chaque modèle récupère indépendamment.  |
| `retryFailed` | `boolean` | Non | Voir les paramètres de l’opération. `default=false` |
| `device` | `string` | Non | auto = CUDA GPU lorsque le moteur voit un, sinon CPU. gpu échoue lorsque CUDA est indisponible. cpu réserve RAM uniquement. `default="auto"`, `enum=["auto", "gpu", "cpu"]` |
| `audioIds` | `array` | Non | Restreint aux actifs spécifiés  |
| `autoLabel` | `boolean` | Non | Catégorisez et taguez les fichiers analysés pour la première fois `default=true` |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation analyze_library
```
