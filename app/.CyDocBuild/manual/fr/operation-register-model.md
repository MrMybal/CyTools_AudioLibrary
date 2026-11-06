---
id: operation-register-model
title: register_model
description: Enregistrer un modèle local, une variante fin-tuned ou une autre version à la place. Plusieurs versions d'un même modelId coexistent ; chacune conserve ses propres embeddings.
section: Référence
order: 200
parent: operations
sourceRevision: e07897d288bad0b4
---

Enregistrer un modèle local, une variante fin-tuned ou une autre version à la place. Plusieurs versions d'un même modelId coexistent ; chacune conserve ses propres embeddings.

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `modelId` | `string` | Oui | Voir les paramètres de l’opération. `pattern="^[A-Za-z][A-Za-z0-9_.-]{0,63}$"` |
| `version` | `string` | Oui | Voir les paramètres de l’opération. `pattern="^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$"` |
| `displayName` | `string` | Oui | Voir les paramètres de l’opération.  |
| `modelType` | `string` | Oui | Voir les paramètres de l’opération. `enum=["AudioTextEmbedding", "AudioEmbedding", "LLM", "AudioUnderstanding"]` |
| `adapter` | `string` | Oui | m2d_clap | hf_clap | omni_embed | hf_causal_lm | file:<absolute adapter.py>  |
| `localPath` | `string` | Oui | Dossier absolu ou fichier de poids ; référencé en place, jamais copié  |
| `capabilities` | `array` | Oui | Voir les paramètres de l’opération.  |
| `embeddingDimension` | `integer` | Non | Voir les paramètres de l’opération. `minimum=1`, `maximum=16384` |
| `requiredSampleRate` | `integer` | Non | Voir les paramètres de l’opération. `minimum=8000`, `maximum=192000` |
| `maximumAudioDuration` | `number` | Non | Voir les paramètres de l’opération. `minimum=0.1` |
| `preferredChunkDuration` | `number` | Non | Voir les paramètres de l’opération. `minimum=0.5`, `maximum=600` |
| `revision` | `string` | Non | Voir les paramètres de l’opération.  |
| `family` | `string` | Non | Voir les paramètres de l’opération.  |
| `provider` | `string` | Non | Voir les paramètres de l’opération.  |
| `repository` | `string` | Non | Voir les paramètres de l’opération.  |
| `licenseName` | `string` | Non | Voir les paramètres de l’opération.  |
| `licenseUrl` | `string` | Non | Voir les paramètres de l’opération.  |
| `engine` | `string` | Non | Voir les paramètres de l’opération. `default="torch"`, `enum=["torch", "base"]` |
| `similarityRange` | `array` | Non | Gamme cosinus mappée à 0..100 % pour affichage  |
| `promptProfile` | `string` | Non | Quel prompt ce modèle a-t-il été formé pour. "generic" est la instruction intégrée avec ses exemples few-shot ; "caption" est le schema clap_prompt/variations/suggested_* . Un modèle n'est jamais reconnu par son nom, il déclare son profil ici. `default="generic"`, `enum=["generic", "caption"]` |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation register_model
```
