---
id: operation-export-bundle
title: export_bundle
description: Copiez une sélection de sons (audioIds) ou tous les sons correspondant à un filtre dans un dossier choisi par l'utilisateur, par exemple pour préparer ce que l'engine de jeu ou un DAW importera. Les originaux ne sont lus que.…
section: Référence
order: 200
parent: operations
sourceRevision: e0debcbbae2ff916
---

Copiez une sélection de sons (audioIds) ou tous les sons correspondant à un filtre dans un dossier choisi par l'utilisateur, par exemple pour préparer ce que l'engine de jeu ou un DAW importera. Les originaux ne sont lus que. Rien n'est jamais surécrit : un fichier déjà présent avec le même contenu est laissé tel quel, un autre avec le même nom mais différent obtient un nom numéroté. Un destination qui placerait des copies à l'intérieur d'un dossier de n'importe quelle Library ou dans un cache est refusée. bundle.json liste chaque fichier avec ses sources, AudioId, durée, tags et catégories ; l'exportation dans le même dossier ajoute à celui-ci.

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `libraryId` | `string` | Oui | Id de la Bibliothèque retourné par create_library ou list_libraries `pattern="^[0-9a-f]{8}$"` |
| `audioIds` | `array` | Non | Voir les paramètres de l’opération.  |
| `filters` | `object` | Non | Tous les actifs correspondant à ces filtres sont copiés aussi (les mêmes filtres que browse_assets). Ne doit pas être vide.  |
| `destination` | `string` | Oui | Chemin absolu vers un dossier ; créé si il n'existe pas  |
| `layout` | `string` | Non | flat = chaque fichier directement dans le destination ; folders = <nom du dossier racine>/<sous dossiers>/<fichier> `default="flat"`, `enum=["flat", "folders"]` |
| `manifest` | `boolean` | Non | Écrivez ou mettez à jour bundle.json dans le destination `default=true` |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation export_bundle
```
