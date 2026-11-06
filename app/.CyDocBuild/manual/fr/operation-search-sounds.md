---
id: operation-search-sounds
title: search_sounds
description: Recherchez des sons dans les bibliothèques audio locales de l'utilisateur à partir d'une description textuelle libre dans n'importe quel langage (ou des sons similaires à un actif connu). Omettez libraryId pour rechercher…
section: Référence
order: 200
parent: operations
sourceRevision: 8796cabf33a129c3
---

Recherchez des sons dans les bibliothèques audio locales de l'utilisateur à partir d'une description textuelle libre dans n'importe quel langage (ou des sons similaires à un actif connu). Omettez libraryId pour rechercher toutes les bibliothèques en même temps. Chaque résultat fournit le chemin absolu du fichier original, la durée, les tags, les catégories, une note de 0 à 100 par modèle et, pour les enregistrements longs, le segment de temps correspondant : suffisant pour proposer des sons à l'utilisateur. Chaque modèle récupère de son propre index ; les classements sont fusionnés avec le Reciprocal Rank Fusion pondéré. Le travail est asynchrone : surveillez cy_get_job et lisez outputs.results lorsque le statut est Terminé.

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `libraryId` | `string` | Non | Facultatif. Absent = recherche de toutes les bibliothèques (les résultats portent libraryId et libraryName). Requis avec similarTo. `pattern="^[0-9a-f]{8}$"` |
| `text` | `string` | Non | gros impact métallique très lourd avec une longue réverbération  |
| `similarTo` | `string` | Non | Recherchez des sons similaires à cet actif (sa représentation d'embedding stockée est la requête) `pattern="^[0-9a-f]{32}$"` |
| `selectionStart` | `number` | Non | Avec similarTo : début de la sélection de temps utilisée comme requête audio, secondes `minimum=0` |
| `selectionEnd` | `number` | Non | Avec similarTo : fin de la sélection de temps, secondes `minimum=0` |
| `models` | `array` | Non | Modèles d'embedding à utiliser. Vide ou absent = tous les modèles actifs pour la Bibliothèque. Chaque modèle récupère indépendamment.  |
| `filters` | `object` | Non | Filtres classiques combinés avec AND. Ils restreignent également une recherche sémantique.  |
| `topK` | `integer` | Non | Voir les paramètres de l’opération. `default=50`, `minimum=1`, `maximum=2000` |
| `llmAssist` | `string` | Non | Petit local LLM pour la compréhension de la requête. auto = uniquement pour des demandes longues, non-anglaises, négatives ou séquentielles. `default="auto"`, `enum=["off", "auto", "always"]` |
| `llmModel` | `string` | Non | modelKey du LLM ; vide = le modèle choisi dans les paramètres de l'application, qui est également utilisé par l'interface `default=""` |
| `weights` | `object` | Non | Poids de fusion de classements par modelKey pour cette recherche  |
| `rrfK` | `integer` | Non | K de la fusion de classements réciproques `default=60`, `minimum=1`, `maximum=1000` |
| `device` | `string` | Non | auto = CUDA GPU lorsque le moteur voit un, sinon CPU. gpu échoue lorsque CUDA est indisponible. cpu réserve RAM uniquement. `default="auto"`, `enum=["auto", "gpu", "cpu"]` |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation search_sounds
```
