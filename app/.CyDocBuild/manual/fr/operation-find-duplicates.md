---
id: operation-find-duplicates
title: find_duplicates
description: Groupe les doubles exacts (taille + hash, confirmés par le SHA-256) ou les doubles probables (similitude d'embedding + durée). Seulement des rapports et des groupes : rien n'est supprimé.
section: Référence
order: 200
parent: operations
sourceRevision: c4a414c0d6bd0af5
---

Groupe les doubles exacts (taille + hash, confirmés par le SHA-256) ou les doubles probables (similitude d'embedding + durée). Seulement des rapports et des groupes : rien n'est supprimé.

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `libraryId` | `string` | Oui | Id de la Bibliothèque retourné par create_library ou list_libraries `pattern="^[0-9a-f]{8}$"` |
| `mode` | `string` | Non | Voir les paramètres de l’opération. `default="exact"`, `enum=["exact", "probable"]` |
| `model` | `string` | Non | modelId@version de list_models `pattern="^[A-Za-z][A-Za-z0-9_.-]{0,63}@[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$"` |
| `threshold` | `number` | Non | Similitude cosinus pour les doubles probables `default=0.985`, `minimum=0.8`, `maximum=1.0` |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation find_duplicates
```
