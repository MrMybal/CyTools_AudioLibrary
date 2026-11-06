---
id: operation-create-library
title: create_library
description: Créez une bibliothèque virtuelle. Les dossiers sont référencés, jamais copiés ou modifiés. Le cache peut vivre sur n’importe quel disque.
section: Référence
order: 200
parent: operations
sourceRevision: cd6e90f538f9011b
---

Créez une bibliothèque virtuelle. Les dossiers sont référencés, jamais copiés ou modifiés. Le cache peut vivre sur n’importe quel disque.

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `name` | `string` | Oui | Voir les paramètres de l’opération.  |
| `cacheLocation` | `string` | Non | Répertoire absolu pour tous les données dérivées (base de données, ondes sonores, embeddings). Vide = data/cache du Tool.  |
| `folders` | `array` | Non | Répertoires audio absolu à ajouter immédiatement  |
| `enableDefaultModels` | `boolean` | Non | Activer les modèles d'embedding par défaut installés `default=true` |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation create_library
```
