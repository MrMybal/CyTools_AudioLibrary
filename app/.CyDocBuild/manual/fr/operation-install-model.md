---
id: operation-install-model
title: install_model
description: Téléchargez (avec reprise), vérifiez et enregistrez un modèle de catalogue. Les licences qui en ont besoin doivent être acceptées personnellement avec acceptLicense=true. Les identifiants ne sont jamais des paramètres.
section: Référence
order: 200
parent: operations
sourceRevision: 8b3ec59d14786907
---

Téléchargez (avec reprise), vérifiez et enregistrez un modèle de catalogue. Les licences qui en ont besoin doivent être acceptées personnellement avec acceptLicense=true. Les identifiants ne sont jamais des paramètres.

## Paramètres {#contract}

| Nom | Type | Obligatoire | Description |
|---|---|---|---|
| `modelKey` | `string` | Oui | modelId@version de list_models `pattern="^[A-Za-z][A-Za-z0-9_.-]{0,63}@[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$"` |
| `acceptLicense` | `boolean` | Non | Votre propre acceptation de la licence du modèle affichée par list_models `default=false` |
| `repair` | `boolean` | Non | Ré-hachez chaque fichier et redéchargez les fichiers corrompus `default=false` |
## Retours {#returns}

Aucun champ nommé n’est déclaré à ce niveau. Consultez le schéma avec `describe-operation` pour connaître sa forme exacte.

## Comportement et accès {#behaviour}

- Autorisations requises : aucune déclarée.
- Moteurs : aucun déclaré.
- Annulation : prise en charge.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe-operation install_model
```
