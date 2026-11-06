---
id: operations
title: Automatisation et API
description: Connectez un client et consultez les opérations disponibles.
section: Référence
order: 80
parent: overview
sourceRevision: 56f70c8ddb3ec175
---

## Ligne de commande {#cli}

Depuis la racine de l’application, utilisez son interpréteur Python privé. `describe` et `list-operations` examinent le contrat public.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe
runtime\python\Scripts\python.exe app\tool.py list-operations
runtime\python\Scripts\python.exe app\tool.py invoke list_libraries --params "{}"
```

## MCP {#mcp}

Configurez votre client MCP pour lancer l’interpréteur privé avec `app/tool.py mcp`, en utilisant le dossier de l’application comme dossier de travail. Reconnectez-le lorsque le catalogue d’opérations exposées change.

## Fichiers des tâches {#task-files}

Les entrées locales acceptent des chemins absolus lisibles et sont importées automatiquement dans l’espace de la tâche. Exportez les résultats utiles avant de terminer la tâche. Ne réutilisez pas les chemins temporaires après nettoyage.

## Opérations {#operations}

- [`list_libraries`](doc:operation-list-libraries)
- [`create_library`](doc:operation-create-library)
- [`update_library`](doc:operation-update-library)
- [`delete_library`](doc:operation-delete-library)
- [`add_folder`](doc:operation-add-folder)
- [`remove_folder`](doc:operation-remove-folder)
- [`set_folder_enabled`](doc:operation-set-folder-enabled)
- [`move_cache`](doc:operation-move-cache)
- [`scan_library`](doc:operation-scan-library)
- [`check_library`](doc:operation-check-library)
- [`analyze_library`](doc:operation-analyze-library)
- [`control_analysis`](doc:operation-control-analysis)
- [`library_status`](doc:operation-library-status)
- [`browse_assets`](doc:operation-browse-assets)
- [`get_asset`](doc:operation-get-asset)
- [`get_waveform`](doc:operation-get-waveform)
- [`update_assets`](doc:operation-update-assets)
- [`export_bundle`](doc:operation-export-bundle)
- [`list_folders`](doc:operation-list-folders)
- [`search_sounds`](doc:operation-search-sounds)
- [`understand_query`](doc:operation-understand-query)
- [`categorize_library`](doc:operation-categorize-library)
- [`find_duplicates`](doc:operation-find-duplicates)
- [`purge_missing`](doc:operation-purge-missing)
- [`suggest_names`](doc:operation-suggest-names)
- [`rename_files`](doc:operation-rename-files)
- [`undo_rename`](doc:operation-undo-rename)
- [`write_metadata`](doc:operation-write-metadata)
- [`list_models`](doc:operation-list-models)
- [`install_model`](doc:operation-install-model)
- [`verify_model`](doc:operation-verify-model)
- [`remove_model`](doc:operation-remove-model)
- [`register_model`](doc:operation-register-model)
- [`remove_model_data`](doc:operation-remove-model-data)
- [`engine_status`](doc:operation-engine-status)
- [`install_engine`](doc:operation-install-engine)
- [`release_models`](doc:operation-release-models)
