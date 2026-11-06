---
id: operations
title: Automation and API
description: Connect a client and inspect the available operations.
section: Reference
order: 80
parent: overview
revision: 56f70c8ddb3ec175
---

## Command line {#cli}

From the application root, use the private Python interpreter. `describe` and `list-operations` inspect the public contract.

```powershell
runtime\python\Scripts\python.exe app\tool.py describe
runtime\python\Scripts\python.exe app\tool.py list-operations
runtime\python\Scripts\python.exe app\tool.py invoke list_libraries --params "{}"
```

## MCP {#mcp}

Configure your MCP client to start the private interpreter with `app/tool.py mcp`, using the application folder as its working directory. Restart the connection when its exposed operation catalogue changes.

## Task files {#task-files}

Local file inputs accept absolute readable paths and are imported into the task workspace automatically. Export wanted results before finishing the task. Do not rely on temporary paths after task cleanup.

## Operations {#operations}

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
