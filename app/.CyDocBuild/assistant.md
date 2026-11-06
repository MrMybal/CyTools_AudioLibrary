# CyTools_AudioLibrary — application integration

Use the installed private Python interpreter and `app/tool.py`. CLI inspection: `describe`, `list-operations`, and `describe-operation OPERATION_ID`; MCP: `mcp`. File inputs accept readable absolute paths and are automatically imported into the task. Export wanted outputs before finishing a temporary task. Never accept a model licence or file modification confirmation for the user.

## Public operation contracts

```json
[
  {
    "id": "list_libraries",
    "name": "List Libraries",
    "description": "Libraries known to this Tool with their folders, cache location and enabled models.",
    "inputSchema": {
      "type": "object",
      "properties": {},
      "required": [],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 67108864
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": false
  },
  {
    "id": "create_library",
    "name": "Create Library",
    "description": "Create a virtual Library. Folders are referenced, never copied or modified. The cache can live on any drive.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "name": {
          "type": "string",
          "minLength": 1,
          "maxLength": 120
        },
        "cacheLocation": {
          "type": "string",
          "description": "Absolute folder for all derived data (database, waveforms, embeddings). Empty = data/cache of the Tool.",
          "x-cy-kind": "Directory"
        },
        "folders": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Absolute audio folders to add immediately"
        },
        "enableDefaultModels": {
          "type": "boolean",
          "default": true,
          "description": "Enable the installed default embedding models"
        }
      },
      "required": [
        "name"
      ],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 67108864
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": false
  },
  {
    "id": "update_library",
    "name": "Update Library",
    "description": "Rename a Library, change its settings, its enabled models or its taxonomy.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "libraryId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}$",
          "description": "LibraryId returned by create_library or list_libraries"
        },
        "name": {
          "type": "string",
          "minLength": 1,
          "maxLength": 120
        },
        "settings": {
          "type": "object",
          "additionalProperties": false,
          "description": "Library settings. Changing segmentation creates a new analysis key: previous embeddings are kept.",
          "properties": {
            "segmentSeconds": {
              "type": "number",
              "minimum": 1,
              "maximum": 120,
              "description": "Window length in seconds for long files (a model may impose its own)"
            },
            "segmentOverlap": {
              "type": "number",
              "minimum": 0,
              "maximum": 60,
              "description": "Overlap between consecutive windows, seconds"
            },
            "maxSegmentsPerFile": {
              "type": "integer",
              "minimum": 1,
              "maximum": 5000
            },
            "computeLoudness": {
              "type": "boolean",
              "description": "Integrated LUFS (ITU-R BS.1770) during the metadata pass"
            },
            "autoTagThreshold": {
              "type": "number",
              "minimum": 0,
              "maximum": 1
            },
            "autoTagsPerFile": {
              "type": "integer",
              "minimum": 0,
              "maximum": 30
            },
            "categoryThreshold": {
              "type": "number",
              "minimum": 0,
              "maximum": 1
            },
            "categoriesPerFile": {
              "type": "integer",
              "minimum": 0,
              "maximum": 10
            },
            "modelWeights": {
              "type": "object",
              "additionalProperties": {
                "type": "number",
                "minimum": 0,
                "maximum": 10
              },
              "description": "Rank-fusion weight per modelKey (default 1.0)"
            },
            "excludePenalty": {
              "type": "number",
              "minimum": 0,
              "maximum": 3,
              "description": "Strength of the penalty for excluded sounds"
            },
            "autoSync": {
              "type": "string",
              "enum": [
                "auto",
                "ask",
                "off"
              ],
              "description": "Standalone background synchronisation: auto = check the folders and update by itself (default); ask = check, then show an Update button; off"
            },
            "autoSyncIntervalSeconds": {
              "type": "integer",
              "minimum": 30,
              "maximum": 86400,
              "description": "Seconds between two background checks"
            },
            "autoAnalyze": {
              "type": "boolean",
              "description": "After an automatic scan, embed new/modified files with the enabled models"
            }
          }
        },
        "enabledModels": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^[A-Za-z][A-Za-z0-9_.-]{0,63}@[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$",
            "description": "modelId@version from list_models"
          },
          "uniqueItems": true,
          "maxItems": 16,
          "description": "Embedding models to use. Empty or absent = every model enabled for the Library. Each model retrieves independently."
        },
        "taxonomy": {
          "type": "object",
          "required": [
            "categories"
          ],
          "additionalProperties": false,
          "properties": {
            "categories": {
              "type": "array",
              "items": {
                "$ref": "#/$defs/category"
              }
            },
            "tags": {
              "type": "array",
              "items": {
                "type": "string"
              },
              "description": "Vocabulary of automatic tags"
            }
          }
        }
      },
      "required": [
        "libraryId"
      ],
      "additionalProperties": false,
      "$defs": {
        "category": {
          "type": "object",
          "required": [
            "id",
            "name"
          ],
          "additionalProperties": false,
          "properties": {
            "id": {
              "type": "string",
              "minLength": 1
            },
            "name": {
              "type": "string",
              "minLength": 1
            },
            "prompts": {
              "type": "array",
              "items": {
                "type": "string"
              },
              "description": "English descriptions used for zero-shot classification"
            },
            "children": {
              "type": "array",
              "items": {
                "$ref": "#/$defs/category"
              }
            }
          }
        }
      }
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 67108864
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": false
  },
  {
    "id": "delete_library",
    "name": "Delete Library",
    "description": "Forget a Library. Audio files are never touched; the cache is deleted only on request.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "libraryId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}$",
          "description": "LibraryId returned by create_library or list_libraries"
        },
        "deleteCache": {
          "type": "boolean",
          "default": false
        }
      },
      "required": [
        "libraryId"
      ],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 67108864
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": false
  },
  {
    "id": "add_folder",
    "name": "Add Folder",
    "description": "Reference one more audio folder (recursive). Run scan_library afterwards.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "libraryId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}$",
          "description": "LibraryId returned by create_library or list_libraries"
        },
        "path": {
          "type": "string",
          "minLength": 1,
          "description": "Audio folder. Absolute path on the machine running the Tool.",
          "x-cy-kind": "Directory"
        }
      },
      "required": [
        "libraryId",
        "path"
      ],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 67108864
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": false
  },
  {
    "id": "remove_folder",
    "name": "Remove Folder",
    "description": "Stop referencing a folder. Its assets become missing and keep their analysis until purge_missing.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "libraryId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}$",
          "description": "LibraryId returned by create_library or list_libraries"
        },
        "rootId": {
          "type": "string"
        }
      },
      "required": [
        "libraryId",
        "rootId"
      ],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 67108864
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": false
  },
  {
    "id": "set_folder_enabled",
    "name": "Enable or Disable Folder",
    "description": "A disabled folder is skipped by scans and hidden from browsing; nothing is deleted.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "libraryId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}$",
          "description": "LibraryId returned by create_library or list_libraries"
        },
        "rootId": {
          "type": "string"
        },
        "enabled": {
          "type": "boolean"
        }
      },
      "required": [
        "libraryId",
        "rootId",
        "enabled"
      ],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 67108864
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": false
  },
  {
    "id": "move_cache",
    "name": "Move Cache",
    "description": "Copy the whole cache of a Library to another location, verify it, then switch. The previous copy is kept.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "libraryId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}$",
          "description": "LibraryId returned by create_library or list_libraries"
        },
        "cacheLocation": {
          "type": "string",
          "minLength": 1,
          "description": "New cache root. Absolute path on the machine running the Tool.",
          "x-cy-kind": "Directory"
        }
      },
      "required": [
        "libraryId",
        "cacheLocation"
      ],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 268435456
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": true
  },
  {
    "id": "scan_library",
    "name": "Scan Library",
    "description": "Incremental recursive scan: new, unchanged, modified, moved, missing and duplicate files, then metadata, loudness and waveform cache for new/modified files only.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "libraryId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}$",
          "description": "LibraryId returned by create_library or list_libraries"
        },
        "rootIds": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Rescan only these folders"
        },
        "analyzeCommon": {
          "type": "boolean",
          "default": true,
          "description": "Also compute metadata + waveform for pending files"
        },
        "retryFailed": {
          "type": "boolean",
          "default": false
        },
        "threads": {
          "type": "integer",
          "minimum": 1,
          "maximum": 32
        }
      },
      "required": [
        "libraryId"
      ],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 1073741824
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": true,
    "estimatedDurationSeconds": 60
  },
  {
    "id": "check_library",
    "name": "Check Library For Changes",
    "description": "Read-only and fast: compares the folders with the database (size and date only) and reports new, modified, missing and restored files, without writing anything. Call scan_library when changed is true.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "libraryId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}$",
          "description": "LibraryId returned by create_library or list_libraries"
        },
        "rootIds": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Check only these folders"
        }
      },
      "required": [
        "libraryId"
      ],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 268435456
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": false
  },
  {
    "id": "analyze_library",
    "name": "Analyze Library",
    "description": "Compute the missing embeddings (whole clip + overlapping segments) for each selected model, then automatic categories and tags. Existing waveforms, metadata and other models' embeddings are never recomputed.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "libraryId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}$",
          "description": "LibraryId returned by create_library or list_libraries"
        },
        "models": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^[A-Za-z][A-Za-z0-9_.-]{0,63}@[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$",
            "description": "modelId@version from list_models"
          },
          "uniqueItems": true,
          "maxItems": 16,
          "description": "Embedding models to use. Empty or absent = every model enabled for the Library. Each model retrieves independently."
        },
        "retryFailed": {
          "type": "boolean",
          "default": false
        },
        "device": {
          "type": "string",
          "enum": [
            "auto",
            "gpu",
            "cpu"
          ],
          "default": "auto",
          "description": "auto = CUDA GPU when the engine sees one, else CPU. gpu fails when CUDA is unavailable. cpu reserves RAM only."
        },
        "audioIds": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^[0-9a-f]{32}$",
            "description": "Stable AudioId of an asset (survives renames and moves)"
          },
          "description": "Restrict to these assets"
        },
        "autoLabel": {
          "type": "boolean",
          "default": true,
          "description": "Categorize and tag newly analyzed files"
        }
      },
      "required": [
        "libraryId"
      ],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 2147483648
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": true,
    "estimatedDurationSeconds": 600
  },
  {
    "id": "control_analysis",
    "name": "Pause or Resume Analysis",
    "description": "Pause or resume the analysis queue of a Library (shared by the UI, CLI and MCP). Use cancel_job to cancel it.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "libraryId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}$",
          "description": "LibraryId returned by create_library or list_libraries"
        },
        "action": {
          "type": "string",
          "enum": [
            "pause",
            "resume"
          ]
        }
      },
      "required": [
        "libraryId",
        "action"
      ],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 67108864
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": false
  },
  {
    "id": "library_status",
    "name": "Library Status",
    "description": "Global figures: files, metadata %, waveforms %, one line per model, stores kept from previous versions, queue state.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "libraryId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}$",
          "description": "LibraryId returned by create_library or list_libraries"
        }
      },
      "required": [
        "libraryId"
      ],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 67108864
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": false
  },
  {
    "id": "browse_assets",
    "name": "Browse Assets",
    "description": "One page of assets with classic filters and sorting (virtualised: only the requested window is materialised).",
    "inputSchema": {
      "type": "object",
      "properties": {
        "libraryId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}$",
          "description": "LibraryId returned by create_library or list_libraries"
        },
        "filters": {
          "type": "object",
          "additionalProperties": false,
          "description": "Classic filters, combined with AND. They also restrict a semantic search.",
          "properties": {
            "text": {
              "type": "string",
              "description": "Words that must appear in the file name, relative path, description or a tag"
            },
            "rootIds": {
              "type": "array",
              "items": {
                "type": "string"
              },
              "description": "Restrict to these folders of the Library"
            },
            "folderPrefix": {
              "type": "string",
              "description": "Relative sub-folder inside the selected root(s), e.g. \"Doors/Metal\""
            },
            "extensions": {
              "type": "array",
              "items": {
                "type": "string"
              },
              "description": "File types, e.g. [\"wav\", \"flac\"]"
            },
            "minDuration": {
              "type": "number",
              "minimum": 0,
              "description": "Seconds"
            },
            "maxDuration": {
              "type": "number",
              "minimum": 0,
              "description": "Seconds"
            },
            "minSampleRate": {
              "type": "integer",
              "minimum": 0,
              "description": "Hz, e.g. 48000"
            },
            "maxSampleRate": {
              "type": "integer",
              "minimum": 0
            },
            "minBitDepth": {
              "type": "integer",
              "minimum": 0
            },
            "channels": {
              "type": "integer",
              "minimum": 1,
              "maximum": 64,
              "description": "1 = mono, 2 = stereo"
            },
            "categories": {
              "type": "array",
              "items": {
                "type": "string"
              },
              "description": "Category ids (user or auto); all must match"
            },
            "tags": {
              "type": "array",
              "items": {
                "type": "string"
              },
              "description": "Tags (user or auto); all must match"
            },
            "favorite": {
              "type": "boolean"
            },
            "minRating": {
              "type": "integer",
              "minimum": 0,
              "maximum": 5
            },
            "duplicatesOnly": {
              "type": "boolean"
            },
            "recent": {
              "type": "boolean",
              "description": "Only sounds that were played"
            },
            "status": {
              "type": "string",
              "enum": [
                "present",
                "missing",
                "any"
              ],
              "default": "present"
            },
            "metadataState": {
              "type": "string",
              "enum": [
                "Ready",
                "Failed",
                "Pending"
              ],
              "description": "Files whose metadata/waveform pass is in this state (Failed = unreadable)"
            },
            "analysisKey": {
              "type": "string"
            },
            "analysisState": {
              "type": "string",
              "enum": [
                "Ready",
                "Failed",
                "NotAnalyzed"
              ]
            }
          }
        },
        "sort": {
          "type": "string",
          "enum": [
            "name",
            "duration",
            "type",
            "folder",
            "size",
            "modified",
            "added",
            "rating",
            "played",
            "sampleRate",
            "channels",
            "category",
            "tags",
            "state"
          ],
          "default": "name",
          "description": "category = first category shown (user ones first), by name; tags = first tag shown; state = failed, pending, then ready."
        },
        "descending": {
          "type": "boolean",
          "default": false
        },
        "offset": {
          "type": "integer",
          "minimum": 0,
          "default": 0
        },
        "limit": {
          "type": "integer",
          "minimum": 1,
          "maximum": 1000,
          "default": 100
        }
      },
      "required": [
        "libraryId"
      ],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 67108864
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": false
  },
  {
    "id": "get_asset",
    "name": "Asset Details",
    "description": "Metadata, levels, user and automatic tags/categories with the model that produced them, captions and per-model analysis states.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "libraryId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}$",
          "description": "LibraryId returned by create_library or list_libraries"
        },
        "audioId": {
          "type": "string",
          "pattern": "^[0-9a-f]{32}$",
          "description": "Stable AudioId of an asset (survives renames and moves)"
        }
      },
      "required": [
        "libraryId",
        "audioId"
      ],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 67108864
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": false
  },
  {
    "id": "get_waveform",
    "name": "Waveform Peaks",
    "description": "Min/max peaks of a time range from the cached pyramid (no decoding).",
    "inputSchema": {
      "type": "object",
      "properties": {
        "libraryId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}$",
          "description": "LibraryId returned by create_library or list_libraries"
        },
        "audioId": {
          "type": "string",
          "pattern": "^[0-9a-f]{32}$",
          "description": "Stable AudioId of an asset (survives renames and moves)"
        },
        "start": {
          "type": "number",
          "minimum": 0,
          "default": 0,
          "description": "Seconds"
        },
        "stop": {
          "type": "number",
          "minimum": 0,
          "description": "Seconds; absent = end of file"
        },
        "columns": {
          "type": "integer",
          "minimum": 16,
          "maximum": 8192,
          "default": 1024
        }
      },
      "required": [
        "libraryId",
        "audioId"
      ],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 67108864
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": false
  },
  {
    "id": "update_assets",
    "name": "Edit Assets",
    "description": "User data (tags, categories, rating, favourite, description, notes) of one asset, a selection (audioIds) or every asset a filter matches, for instance one folder: filters {\"rootIds\": [rootId], \"folderPrefix\": \"Impacts/Metal\"}. Only the Library database changes; audio files are never written here. Automatic tags and categories are stored apart and never overwritten by this operation, nor user data by a re-analysis.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "libraryId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}$",
          "description": "LibraryId returned by create_library or list_libraries"
        },
        "audioIds": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^[0-9a-f]{32}$",
            "description": "Stable AudioId of an asset (survives renames and moves)"
          },
          "minItems": 1,
          "maxItems": 10000
        },
        "filters": {
          "type": "object",
          "additionalProperties": false,
          "description": "Every asset these filters match is edited too (same filters as browse_assets). Must not be empty.",
          "properties": {
            "text": {
              "type": "string",
              "description": "Words that must appear in the file name, relative path, description or a tag"
            },
            "rootIds": {
              "type": "array",
              "items": {
                "type": "string"
              },
              "description": "Restrict to these folders of the Library"
            },
            "folderPrefix": {
              "type": "string",
              "description": "Relative sub-folder inside the selected root(s), e.g. \"Doors/Metal\""
            },
            "extensions": {
              "type": "array",
              "items": {
                "type": "string"
              },
              "description": "File types, e.g. [\"wav\", \"flac\"]"
            },
            "minDuration": {
              "type": "number",
              "minimum": 0,
              "description": "Seconds"
            },
            "maxDuration": {
              "type": "number",
              "minimum": 0,
              "description": "Seconds"
            },
            "minSampleRate": {
              "type": "integer",
              "minimum": 0,
              "description": "Hz, e.g. 48000"
            },
            "maxSampleRate": {
              "type": "integer",
              "minimum": 0
            },
            "minBitDepth": {
              "type": "integer",
              "minimum": 0
            },
            "channels": {
              "type": "integer",
              "minimum": 1,
              "maximum": 64,
              "description": "1 = mono, 2 = stereo"
            },
            "categories": {
              "type": "array",
              "items": {
                "type": "string"
              },
              "description": "Category ids (user or auto); all must match"
            },
            "tags": {
              "type": "array",
              "items": {
                "type": "string"
              },
              "description": "Tags (user or auto); all must match"
            },
            "favorite": {
              "type": "boolean"
            },
            "minRating": {
              "type": "integer",
              "minimum": 0,
              "maximum": 5
            },
            "duplicatesOnly": {
              "type": "boolean"
            },
            "recent": {
              "type": "boolean",
              "description": "Only sounds that were played"
            },
            "status": {
              "type": "string",
              "enum": [
                "present",
                "missing",
                "any"
              ],
              "default": "present"
            },
            "metadataState": {
              "type": "string",
              "enum": [
                "Ready",
                "Failed",
                "Pending"
              ],
              "description": "Files whose metadata/waveform pass is in this state (Failed = unreadable)"
            },
            "analysisKey": {
              "type": "string"
            },
            "analysisState": {
              "type": "string",
              "enum": [
                "Ready",
                "Failed",
                "NotAnalyzed"
              ]
            }
          }
        },
        "setTags": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Replace the user tags"
        },
        "addTags": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "removeTags": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "setCategories": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Replace the user categories (category ids)"
        },
        "addCategories": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Add user categories (category ids), keeping the others"
        },
        "removeCategories": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Remove these user categories (category ids)"
        },
        "favorite": {
          "type": "boolean"
        },
        "rating": {
          "type": "integer",
          "minimum": 0,
          "maximum": 5
        },
        "description": {
          "type": "string",
          "maxLength": 4000
        },
        "notes": {
          "type": "string",
          "maxLength": 20000,
          "description": "Replace the notes"
        },
        "appendNotes": {
          "type": "string",
          "maxLength": 4000,
          "description": "Add this line after the existing notes of every target, never replacing them"
        }
      },
      "required": [
        "libraryId"
      ],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 67108864
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": true
  },
  {
    "id": "export_bundle",
    "name": "Create Bundle",
    "description": "Copy a selection of sounds (audioIds) or every sound a filter matches into a folder the user chooses, for instance to prepare what a game engine or a DAW will import. The originals are only read. Nothing is ever overwritten: a file already present with the same content is left as it is, a different one with the same name gets a numbered name. A destination that would put copies inside a folder of any Library or inside a cache is refused. bundle.json lists every file with its source, AudioId, duration, tags and categories; exporting into the same folder again adds to it.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "libraryId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}$",
          "description": "LibraryId returned by create_library or list_libraries"
        },
        "audioIds": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^[0-9a-f]{32}$",
            "description": "Stable AudioId of an asset (survives renames and moves)"
          },
          "minItems": 1,
          "maxItems": 10000
        },
        "filters": {
          "type": "object",
          "additionalProperties": false,
          "description": "Every asset these filters match is copied too (same filters as browse_assets). Must not be empty.",
          "properties": {
            "text": {
              "type": "string",
              "description": "Words that must appear in the file name, relative path, description or a tag"
            },
            "rootIds": {
              "type": "array",
              "items": {
                "type": "string"
              },
              "description": "Restrict to these folders of the Library"
            },
            "folderPrefix": {
              "type": "string",
              "description": "Relative sub-folder inside the selected root(s), e.g. \"Doors/Metal\""
            },
            "extensions": {
              "type": "array",
              "items": {
                "type": "string"
              },
              "description": "File types, e.g. [\"wav\", \"flac\"]"
            },
            "minDuration": {
              "type": "number",
              "minimum": 0,
              "description": "Seconds"
            },
            "maxDuration": {
              "type": "number",
              "minimum": 0,
              "description": "Seconds"
            },
            "minSampleRate": {
              "type": "integer",
              "minimum": 0,
              "description": "Hz, e.g. 48000"
            },
            "maxSampleRate": {
              "type": "integer",
              "minimum": 0
            },
            "minBitDepth": {
              "type": "integer",
              "minimum": 0
            },
            "channels": {
              "type": "integer",
              "minimum": 1,
              "maximum": 64,
              "description": "1 = mono, 2 = stereo"
            },
            "categories": {
              "type": "array",
              "items": {
                "type": "string"
              },
              "description": "Category ids (user or auto); all must match"
            },
            "tags": {
              "type": "array",
              "items": {
                "type": "string"
              },
              "description": "Tags (user or auto); all must match"
            },
            "favorite": {
              "type": "boolean"
            },
            "minRating": {
              "type": "integer",
              "minimum": 0,
              "maximum": 5
            },
            "duplicatesOnly": {
              "type": "boolean"
            },
            "recent": {
              "type": "boolean",
              "description": "Only sounds that were played"
            },
            "status": {
              "type": "string",
              "enum": [
                "present",
                "missing",
                "any"
              ],
              "default": "present"
            },
            "metadataState": {
              "type": "string",
              "enum": [
                "Ready",
                "Failed",
                "Pending"
              ],
              "description": "Files whose metadata/waveform pass is in this state (Failed = unreadable)"
            },
            "analysisKey": {
              "type": "string"
            },
            "analysisState": {
              "type": "string",
              "enum": [
                "Ready",
                "Failed",
                "NotAnalyzed"
              ]
            }
          }
        },
        "destination": {
          "type": "string",
          "minLength": 3,
          "description": "Absolute folder path; created if it does not exist"
        },
        "layout": {
          "type": "string",
          "enum": [
            "flat",
            "folders"
          ],
          "default": "flat",
          "description": "flat = every file directly in the destination; folders = <root folder name>/<sub folders>/<file>"
        },
        "manifest": {
          "type": "boolean",
          "default": true,
          "description": "Write or update bundle.json in the destination"
        }
      },
      "required": [
        "libraryId",
        "destination"
      ],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 67108864
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": true
  },
  {
    "id": "list_folders",
    "name": "List Folders",
    "description": "Folder structure of a Library as its audio files describe it: every folder with its recursive and direct file counts, per root folder. Use a path from here as filters.folderPrefix (with rootIds) in browse_assets, update_assets, or to collect audioIds for analyze_library, suggest_names and write_metadata.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "libraryId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}$",
          "description": "LibraryId returned by create_library or list_libraries"
        },
        "rootId": {
          "type": "string",
          "description": "Only this root folder"
        },
        "folderPrefix": {
          "type": "string",
          "description": "Start below this folder, relative to the root, '/' separated"
        },
        "maxDepth": {
          "type": "integer",
          "minimum": 0,
          "maximum": 64,
          "default": 2,
          "description": "Levels below the start; 0 = all"
        }
      },
      "required": [
        "libraryId"
      ],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 67108864
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": false
  },
  {
    "id": "search_sounds",
    "name": "Search Sounds",
    "description": "Find sounds in the user's local audio Libraries from a free-text description in any language (or sounds similar to a known asset). Omit libraryId to search every Library at once. Each result gives the absolute path of the original file, duration, tags, categories, a 0-100 score per model and, for long recordings, the matching time segment: enough to propose sounds to the user. Each model retrieves from its own index; ranks are fused with weighted Reciprocal Rank Fusion. The job is asynchronous: poll cy_get_job and read outputs.results when Completed.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "libraryId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}$",
          "description": "Optional. Absent = search all Libraries (results carry libraryId and libraryName). Required with similarTo."
        },
        "text": {
          "type": "string",
          "maxLength": 1000,
          "description": "Free text in any language, e.g. \"gros impact métallique très lourd avec une longue réverbération\"",
          "x-cy-kind": "MultilineString"
        },
        "similarTo": {
          "type": "string",
          "pattern": "^[0-9a-f]{32}$",
          "description": "Find sounds similar to this asset (its stored embedding is the query)"
        },
        "selectionStart": {
          "type": "number",
          "minimum": 0,
          "description": "With similarTo: start of the time selection used as the audio query, seconds"
        },
        "selectionEnd": {
          "type": "number",
          "minimum": 0,
          "description": "With similarTo: end of the time selection, seconds"
        },
        "models": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^[A-Za-z][A-Za-z0-9_.-]{0,63}@[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$",
            "description": "modelId@version from list_models"
          },
          "uniqueItems": true,
          "maxItems": 16,
          "description": "Embedding models to use. Empty or absent = every model enabled for the Library. Each model retrieves independently."
        },
        "filters": {
          "type": "object",
          "additionalProperties": false,
          "description": "Classic filters, combined with AND. They also restrict a semantic search.",
          "properties": {
            "text": {
              "type": "string",
              "description": "Words that must appear in the file name, relative path, description or a tag"
            },
            "rootIds": {
              "type": "array",
              "items": {
                "type": "string"
              },
              "description": "Restrict to these folders of the Library"
            },
            "folderPrefix": {
              "type": "string",
              "description": "Relative sub-folder inside the selected root(s), e.g. \"Doors/Metal\""
            },
            "extensions": {
              "type": "array",
              "items": {
                "type": "string"
              },
              "description": "File types, e.g. [\"wav\", \"flac\"]"
            },
            "minDuration": {
              "type": "number",
              "minimum": 0,
              "description": "Seconds"
            },
            "maxDuration": {
              "type": "number",
              "minimum": 0,
              "description": "Seconds"
            },
            "minSampleRate": {
              "type": "integer",
              "minimum": 0,
              "description": "Hz, e.g. 48000"
            },
            "maxSampleRate": {
              "type": "integer",
              "minimum": 0
            },
            "minBitDepth": {
              "type": "integer",
              "minimum": 0
            },
            "channels": {
              "type": "integer",
              "minimum": 1,
              "maximum": 64,
              "description": "1 = mono, 2 = stereo"
            },
            "categories": {
              "type": "array",
              "items": {
                "type": "string"
              },
              "description": "Category ids (user or auto); all must match"
            },
            "tags": {
              "type": "array",
              "items": {
                "type": "string"
              },
              "description": "Tags (user or auto); all must match"
            },
            "favorite": {
              "type": "boolean"
            },
            "minRating": {
              "type": "integer",
              "minimum": 0,
              "maximum": 5
            },
            "duplicatesOnly": {
              "type": "boolean"
            },
            "recent": {
              "type": "boolean",
              "description": "Only sounds that were played"
            },
            "status": {
              "type": "string",
              "enum": [
                "present",
                "missing",
                "any"
              ],
              "default": "present"
            },
            "metadataState": {
              "type": "string",
              "enum": [
                "Ready",
                "Failed",
                "Pending"
              ],
              "description": "Files whose metadata/waveform pass is in this state (Failed = unreadable)"
            },
            "analysisKey": {
              "type": "string"
            },
            "analysisState": {
              "type": "string",
              "enum": [
                "Ready",
                "Failed",
                "NotAnalyzed"
              ]
            }
          }
        },
        "topK": {
          "type": "integer",
          "minimum": 1,
          "maximum": 2000,
          "default": 50
        },
        "llmAssist": {
          "type": "string",
          "enum": [
            "off",
            "auto",
            "always"
          ],
          "default": "auto",
          "description": "Small local LLM for query understanding. auto = only for long, non-English, negated or sequential requests."
        },
        "llmModel": {
          "type": "string",
          "default": "",
          "description": "modelKey of the LLM; empty = the model chosen in the application settings, which is what the interface uses too"
        },
        "weights": {
          "type": "object",
          "additionalProperties": {
            "type": "number",
            "minimum": 0,
            "maximum": 10
          },
          "description": "Rank-fusion weight per modelKey for this search"
        },
        "rrfK": {
          "type": "integer",
          "minimum": 1,
          "maximum": 1000,
          "default": 60,
          "description": "K of Reciprocal Rank Fusion"
        },
        "device": {
          "type": "string",
          "enum": [
            "auto",
            "gpu",
            "cpu"
          ],
          "default": "auto",
          "description": "auto = CUDA GPU when the engine sees one, else CPU. gpu fails when CUDA is unavailable. cpu reserves RAM only."
        }
      },
      "required": [],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 1073741824
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": true,
    "outputs": [
      {
        "id": "results",
        "name": "Search results",
        "type": "File",
        "mimeType": "application/json",
        "description": "outputs/search-results.json: same content as the job outputs, paths are absolute paths of the original audio files"
      }
    ]
  },
  {
    "id": "understand_query",
    "name": "Understand Query",
    "description": "Turn a free-form request into the stable structured query (events, properties, environment, exclude, temporal, queries) without searching.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "text": {
          "type": "string",
          "minLength": 1,
          "maxLength": 1000
        },
        "llmAssist": {
          "type": "string",
          "enum": [
            "off",
            "auto",
            "always"
          ],
          "default": "always"
        },
        "llmModel": {
          "type": "string",
          "default": ""
        },
        "device": {
          "type": "string",
          "enum": [
            "auto",
            "gpu",
            "cpu"
          ],
          "default": "auto",
          "description": "auto = CUDA GPU when the engine sees one, else CPU. gpu fails when CUDA is unavailable. cpu reserves RAM only."
        }
      },
      "required": [
        "text"
      ],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 1073741824
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": false
  },
  {
    "id": "categorize_library",
    "name": "Categorize Library",
    "description": "Recompute automatic categories and tags from stored embeddings with the current taxonomy. No audio decoding; user tags untouched.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "libraryId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}$",
          "description": "LibraryId returned by create_library or list_libraries"
        },
        "models": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^[A-Za-z][A-Za-z0-9_.-]{0,63}@[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$",
            "description": "modelId@version from list_models"
          },
          "uniqueItems": true,
          "maxItems": 16,
          "description": "Embedding models to use. Empty or absent = every model enabled for the Library. Each model retrieves independently."
        },
        "device": {
          "type": "string",
          "enum": [
            "auto",
            "gpu",
            "cpu"
          ],
          "default": "auto",
          "description": "auto = CUDA GPU when the engine sees one, else CPU. gpu fails when CUDA is unavailable. cpu reserves RAM only."
        }
      },
      "required": [
        "libraryId"
      ],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 1073741824
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": true
  },
  {
    "id": "find_duplicates",
    "name": "Find Duplicates",
    "description": "Group exact duplicates (size + hash, confirmed by SHA-256) or probable duplicates (embedding similarity + duration). Reports and groups only: nothing is deleted.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "libraryId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}$",
          "description": "LibraryId returned by create_library or list_libraries"
        },
        "mode": {
          "type": "string",
          "enum": [
            "exact",
            "probable"
          ],
          "default": "exact"
        },
        "model": {
          "type": "string",
          "pattern": "^[A-Za-z][A-Za-z0-9_.-]{0,63}@[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$",
          "description": "modelId@version from list_models"
        },
        "threshold": {
          "type": "number",
          "minimum": 0.8,
          "maximum": 1.0,
          "default": 0.985,
          "description": "Cosine similarity for probable duplicates"
        }
      },
      "required": [
        "libraryId"
      ],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 2147483648
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": true
  },
  {
    "id": "purge_missing",
    "name": "Purge Missing Assets",
    "description": "Delete the database rows and analysis of assets whose file is missing. Explicit; original files are not concerned.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "libraryId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}$",
          "description": "LibraryId returned by create_library or list_libraries"
        },
        "confirm": {
          "type": "boolean",
          "const": true
        }
      },
      "required": [
        "libraryId",
        "confirm"
      ],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 67108864
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": false
  },
  {
    "id": "suggest_names",
    "name": "Suggest File Names",
    "description": "Read-only. Proposes descriptive names (category + tags) for badly named files such as sound_01.wav or ZOOM0012.wav. Returns a plan; nothing is renamed.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "libraryId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}$",
          "description": "LibraryId returned by create_library or list_libraries"
        },
        "audioIds": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^[0-9a-f]{32}$",
            "description": "Stable AudioId of an asset (survives renames and moves)"
          },
          "maxItems": 10000,
          "description": "Absent = whole Library"
        },
        "onlyBadlyNamed": {
          "type": "boolean",
          "default": true,
          "description": "false = propose a name for every listed file"
        },
        "template": {
          "type": "string",
          "default": "{category}_{tags}",
          "maxLength": 120,
          "description": "Fields: {category} {tags} {original} {duration}"
        },
        "maxTags": {
          "type": "integer",
          "minimum": 0,
          "maximum": 8,
          "default": 3
        },
        "limit": {
          "type": "integer",
          "minimum": 1,
          "maximum": 5000,
          "default": 500
        }
      },
      "required": [
        "libraryId"
      ],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 268435456
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": false
  },
  {
    "id": "rename_files",
    "name": "Rename Files",
    "description": "CHANGES ORIGINAL FILES. Renames files on disk inside their folder (never overwrites, extension kept). AudioId, tags, waveform and embeddings follow the file. Journalled: undo_rename reverses the last batch.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "libraryId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}$",
          "description": "LibraryId returned by create_library or list_libraries"
        },
        "renames": {
          "type": "array",
          "minItems": 1,
          "maxItems": 5000,
          "items": {
            "type": "object",
            "required": [
              "audioId",
              "newName"
            ],
            "additionalProperties": false,
            "properties": {
              "audioId": {
                "type": "string",
                "pattern": "^[0-9a-f]{32}$",
                "description": "Stable AudioId of an asset (survives renames and moves)"
              },
              "newName": {
                "type": "string",
                "minLength": 1,
                "maxLength": 200,
                "description": "File name with the same extension, no folder"
              }
            }
          }
        },
        "confirm": {
          "type": "boolean",
          "const": true,
          "description": "Must be true. This operation changes the user's original files: an AI client must show the plan to the user and obtain an explicit yes first."
        }
      },
      "required": [
        "libraryId",
        "renames",
        "confirm"
      ],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 67108864
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": false
  },
  {
    "id": "undo_rename",
    "name": "Undo Last Rename",
    "description": "CHANGES ORIGINAL FILES. Restores the names of the most recent rename batch that was not undone yet.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "libraryId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}$",
          "description": "LibraryId returned by create_library or list_libraries"
        },
        "confirm": {
          "type": "boolean",
          "const": true,
          "description": "Must be true. This operation changes the user's original files: an AI client must show the plan to the user and obtain an explicit yes first."
        }
      },
      "required": [
        "libraryId",
        "confirm"
      ],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 67108864
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": false
  },
  {
    "id": "write_metadata",
    "name": "Write Metadata Into Files",
    "description": "CHANGES ORIGINAL FILES. Writes description, tags, categories, rating and AudioId into the files themselves (ID3 for WAV/AIFF/MP3, Vorbis comments for FLAC/OGG/Opus, MP4 atoms for M4A). Tags are written into a copy, the decoded audio is verified identical, then the copy replaces the original; a backup goes to the Library cache by default. Embeddings stay valid.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "libraryId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}$",
          "description": "LibraryId returned by create_library or list_libraries"
        },
        "audioIds": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^[0-9a-f]{32}$",
            "description": "Stable AudioId of an asset (survives renames and moves)"
          },
          "minItems": 1,
          "maxItems": 5000
        },
        "fields": {
          "type": "array",
          "uniqueItems": true,
          "items": {
            "type": "string",
            "enum": [
              "description",
              "tags",
              "categories",
              "rating",
              "audioId"
            ]
          },
          "description": "Absent = all"
        },
        "includeAutoTags": {
          "type": "boolean",
          "default": true,
          "description": "false = user tags only"
        },
        "backup": {
          "type": "boolean",
          "default": true,
          "description": "Keep the untouched original in <cache>/Common/FileOperations/Backups"
        },
        "confirm": {
          "type": "boolean",
          "const": true,
          "description": "Must be true. This operation changes the user's original files: an AI client must show the plan to the user and obtain an explicit yes first."
        }
      },
      "required": [
        "libraryId",
        "audioIds",
        "confirm"
      ],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 536870912
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": true
  },
  {
    "id": "list_models",
    "name": "List Models",
    "description": "Model registry: embedding models, LLMs and declared extension points, with version, revision, hash, capabilities, licence, size and installation state.",
    "inputSchema": {
      "type": "object",
      "properties": {},
      "required": [],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 67108864
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": false
  },
  {
    "id": "install_model",
    "name": "Install Model",
    "description": "Download (with resume), verify and register a catalogue model. Licences that require it must be accepted personally with acceptLicense=true. Credentials are never parameters.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "modelKey": {
          "type": "string",
          "pattern": "^[A-Za-z][A-Za-z0-9_.-]{0,63}@[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$",
          "description": "modelId@version from list_models"
        },
        "acceptLicense": {
          "type": "boolean",
          "default": false,
          "description": "Your own acceptance of the model licence shown by list_models"
        },
        "repair": {
          "type": "boolean",
          "default": false,
          "description": "Re-hash every file and download corrupted ones again"
        }
      },
      "required": [
        "modelKey"
      ],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 536870912
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": true,
    "estimatedDurationSeconds": 600
  },
  {
    "id": "verify_model",
    "name": "Verify Model",
    "description": "Re-hash the installed files of a model against its receipt.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "modelKey": {
          "type": "string",
          "pattern": "^[A-Za-z][A-Za-z0-9_.-]{0,63}@[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$",
          "description": "modelId@version from list_models"
        }
      },
      "required": [
        "modelKey"
      ],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 268435456
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": true
  },
  {
    "id": "remove_model",
    "name": "Remove Model",
    "description": "Uninstall the weights of a catalogue model, or unregister a custom model (its files are never deleted). Analysis data of each Library is kept unless deleteAnalysis is true.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "modelKey": {
          "type": "string",
          "pattern": "^[A-Za-z][A-Za-z0-9_.-]{0,63}@[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$",
          "description": "modelId@version from list_models"
        },
        "deleteAnalysis": {
          "type": "boolean",
          "default": false,
          "description": "Also delete the embeddings/indexes of this model in every Library"
        }
      },
      "required": [
        "modelKey"
      ],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 67108864
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": false
  },
  {
    "id": "register_model",
    "name": "Register Custom Model",
    "description": "Register a local model, a fine-tuned variant or another version, in place. Several versions of one modelId coexist; each keeps its own embeddings.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "modelId": {
          "type": "string",
          "pattern": "^[A-Za-z][A-Za-z0-9_.-]{0,63}$"
        },
        "version": {
          "type": "string",
          "pattern": "^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$"
        },
        "displayName": {
          "type": "string",
          "minLength": 1
        },
        "modelType": {
          "type": "string",
          "enum": [
            "AudioTextEmbedding",
            "AudioEmbedding",
            "LLM",
            "AudioUnderstanding"
          ]
        },
        "adapter": {
          "type": "string",
          "description": "m2d_clap | hf_clap | omni_embed | hf_causal_lm | file:<absolute adapter.py>"
        },
        "localPath": {
          "type": "string",
          "description": "Absolute folder or weight file; referenced in place, never copied"
        },
        "capabilities": {
          "type": "array",
          "minItems": 1,
          "items": {
            "type": "string",
            "enum": [
              "AudioEmbedding",
              "TextEmbedding",
              "ZeroShotTagging",
              "Tagging",
              "Classification",
              "Captioning",
              "Reranking",
              "QuestionAnswering",
              "QueryUnderstanding",
              "QueryExpansion",
              "Translation",
              "StructuredOutput"
            ]
          }
        },
        "embeddingDimension": {
          "type": "integer",
          "minimum": 1,
          "maximum": 16384
        },
        "requiredSampleRate": {
          "type": "integer",
          "minimum": 8000,
          "maximum": 192000
        },
        "maximumAudioDuration": {
          "type": "number",
          "minimum": 0.1
        },
        "preferredChunkDuration": {
          "type": "number",
          "minimum": 0.5,
          "maximum": 600
        },
        "revision": {
          "type": "string"
        },
        "family": {
          "type": "string"
        },
        "provider": {
          "type": "string"
        },
        "repository": {
          "type": "string"
        },
        "licenseName": {
          "type": "string"
        },
        "licenseUrl": {
          "type": "string"
        },
        "engine": {
          "type": "string",
          "enum": [
            "torch",
            "base"
          ],
          "default": "torch"
        },
        "similarityRange": {
          "type": "array",
          "items": {
            "type": "number"
          },
          "minItems": 2,
          "maxItems": 2,
          "description": "Cosine range mapped to 0..100 % for display"
        },
        "promptProfile": {
          "type": "string",
          "enum": [
            "generic",
            "caption"
          ],
          "default": "generic",
          "description": "Which prompt this model was trained for. \"generic\" is the built-in instruction with its few-shot examples; \"caption\" is the clap_prompt/variations/suggested_* schema. A model is never recognised by its name, it declares its profile here."
        }
      },
      "required": [
        "modelId",
        "version",
        "displayName",
        "modelType",
        "adapter",
        "localPath",
        "capabilities"
      ],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 268435456
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": false
  },
  {
    "id": "remove_model_data",
    "name": "Remove Analysis Data",
    "description": "Delete one embedding store (analysis key) of a Library, e.g. the data of a previous model version. Other models and versions are untouched.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "libraryId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}$",
          "description": "LibraryId returned by create_library or list_libraries"
        },
        "analysisKey": {
          "type": "string",
          "pattern": "^[0-9a-f]{16}$"
        }
      },
      "required": [
        "libraryId",
        "analysisKey"
      ],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 67108864
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": false
  },
  {
    "id": "engine_status",
    "name": "Engine Status",
    "description": "State of the private AI engine environment, its pinned sources and the models currently loaded in the worker.",
    "inputSchema": {
      "type": "object",
      "properties": {},
      "required": [],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 67108864
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": false
  },
  {
    "id": "install_engine",
    "name": "Install AI Engine",
    "description": "Create the private PyTorch environment at its final path and fetch the pinned engine sources. Long: several GB.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "cpuOnly": {
          "type": "boolean",
          "default": false
        }
      },
      "required": [],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 1073741824
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": true,
    "estimatedDurationSeconds": 1200
  },
  {
    "id": "release_models",
    "name": "Release Models",
    "description": "Unload every model and stop the engine worker now (frees RAM/VRAM). Refused while an analysis or search is running.",
    "inputSchema": {
      "type": "object",
      "properties": {},
      "required": [],
      "additionalProperties": false
    },
    "outputSchema": {
      "type": "object",
      "additionalProperties": true
    },
    "resourceRequirements": {
      "ramBytes": 67108864
    },
    "supportedBackends": [],
    "permissions": [],
    "canRunAsync": true,
    "canCancel": true,
    "supportsProgress": false
  }
]
```

## Host project instructions

# Creating and maintaining CyTools_AudioLibrary

## Rules specific to this Tool (read first)

1. **Never accept a licence for the user.** `install_model` takes `acceptLicense`; it is the user's personal
   acceptance. An agent (CLI, MCP, tests, validation scripts) must ask the user and wait for an explicit yes
   for each model before passing `true`, and must never tick, default or persist the acceptance box of the
   interface. A licence accepted on someone's behalf is not an acceptance at all, and it cannot be taken back.
   Models without `requiresAcceptance` in the catalogue may be installed without asking.
2. **No branching on a model name** anywhere in `audiolib/` or `gui/`. A model is a descriptor + an adapter +
   capabilities. A new model = a catalogue entry (`scripts/build_catalog.py`, which reads sizes/hashes from the
   providers, nothing guessed) or `register_model`; a new architecture = one file in `adapters/`.
3. **Never mix embeddings of different models**, never reuse a store across analysis keys. Fusion is on ranks.
4. **Nothing is written next to the audio files**; files are opened read-only; nothing is deleted automatically
   (duplicates, missing files, previous caches, previous model data, custom model files). The only exceptions are the
   two File Tools operations, `rename_files` (+ `undo_rename`) and `write_metadata`, all in
   `audiolib/fileops.py`. They take `confirm: true`. **Same principle as a licence: an agent never sets `confirm` on its
   own.** Call `suggest_names` (read-only), show the plan or the list of files to the user, wait for an explicit yes,
   then apply. Never call them from a background path, a test on real folders, or a validation script: their tests
   use generated fixture files only. Keep the verified-copy + backup logic of `write_metadata` intact.
   The background synchronisation (`check_library` → `scan_library`) only reads the folders.
5. User tags, user categories, notes, rating and favourite are never touched by an analysis or a re-labelling.
6. Only `worker.py` and `adapters/` may import PyTorch/transformers. `audiolib/`, `tool.py` and `gui/` must import
   without them (the fixture tests run in the base runtime).
7. Windows pitfalls already met here: reserved folder names (`aux`, `con`, `nul`...), backslashes lost when source
   text goes through a shell heredoc (write C++/regex files with a file tool and let `/WX` catch it), Linux pickles
   containing `PosixPath`, and the case-insensitive filesystem (`Docs/Validation.md` is the SDK's file: the Tool's
   report is `Docs/AudioLibrary-Validation.md`).
8. After changing `build_manifest.py`, `scripts/build_catalog.py` or `locales/audiolibrary.fr.json`, regenerate:
   `build_catalog.py` → `build_manifest.py` → `scripts/merge_locales.py`, then run `cytools validate` and the tests.
9. The interface look is CyUI: `cyui.py` is a Python port of the C++ CyUI library. Take colours from `cyui.palette()` by
   role (never a colour literal), sizes through `cyui.dp()`, one primary button per view, icon buttons with a tooltip,
   settings as property tables in sections, and an empty panel always says why. Literal texts given to `cy.*` widgets
   are checked by `tests/test_locales.py` like `imgui.*` labels. Check a change in the five themes (`--ui-test-theme=`).
10. Report measured facts only. Keep *real run*, *fixtures* and *not verified* apart, as the validation report does.

## Generic CyTools rules (from the scaffold)

Mesh Tools must follow Docs/MeshViewer.md: use --desktop --mesh-viewer, open completed
results in the embedded viewport, provide orbit/free mouse-keyboard navigation,
close inspection, scene presets and studio/sun lighting. Static images are insufficient.

Read Docs/SharedInstallation.md. Provide configurable local/shared download storage
and explicit versioned CUDA Toolkit selection. Keep Python private, never move
existing models or accept provider terms implicitly. Expose access-required states
and official links to users and AI clients. Ship without weights and heavy caches.

Read README.md, CyTool.json and tool.py before modifying this tool.
Read Docs/Localization.md. English is the default UI language; French is selectable
and persisted. Options includes language, theme, text scale and component licenses.
Add every new visible string to app/locales/ui.json (en/fr); never translate user data.
Read Docs/GenerationConfigurations.md. Save/load configuration and optional generation
autosave are mandatory. Use explicit configure_generation callbacks; exclude secrets.
For desktop layout these files are inside app/. Read Docs/StandaloneDelivery.md too.
Every user-facing Tool must ship a usable Dear ImGui UI, a Windows .exe and a suitable
Linux launcher. Final root: launcher(s), LISEZ-MOI.md, app/, data/, runtime/ only.
Provide guided model access/download/resume in the UI and staged GitHub updates with
rollback and data preservation. Do not claim a scaffold is a finished application.
Read CyToolsGuide.md (local copy) or CyToolsCore Docs/AgentGuide.md as the implementation contract.
Run `cytools docs` to locate the complete documentation installed with the SDK.

1. Declare every operation in CyTool.json: inputSchema, outputSchema, supportedBackends,
   permissions, resourceRequirements and actual platform support.
2. Register one handler per declared operation in create_runtime().
3. Handler signature: handler(context, parameters) -> JSON-serializable outputs.
4. Check context.cancellation during loops; use context.cancellation.sleep() for waits.
5. Create outputs using context.path('outputs/name.ext'). Never share a fixed output path.
6. Use context.progress(percent, currentStep='...') when supportsProgress is true.
7. Use runtime.register(id, handler, estimate=...) for parameter-dependent RAM/VRAM.
8. Do not implement a second scheduler, job registry, authentication system or MCP parser.
9. No UI, specific AI model or external CLI is required by the core.
10. Treat external files and executable arguments as untrusted; use argv, never shell interpolation.
11. Add real operation tests (invalid inputs, failure, cancellation, output validity).
12. Run: cytools validate CyTool.json; python -m unittest -v; python tool.py describe;
    python tool.py invoke echo --params-file params.json.
13. Document dependencies, model licenses, platform verification and limitations honestly.
14. A descriptor does not implement a backend. Do not claim a capability without code and tests.

User operation parameters cannot choose clientId, owner or a different session.
Permissions belong to the authenticated transport context. Heavy/untrusted runtimes
belong in ProcessWorker; in-process cancellation is cooperative, not forcible.
# Standalone diagnostics and model extensions

Read Docs/StandaloneDiagnosticsAndModels.md. Ship a selectable/copyable application log,
explicit planned/actual video resolution, a local model library and compatible LoRA/device
controls. Save the effective selections in generation recipes. Do not claim unsupported
CPU paths, arbitrary architecture compatibility or generic four-step acceleration.


Lire [Docs/FullOperationAccess.md](Docs/FullOperationAccess.md) : inventaire des capacités natives, parité complète des options métier entre IA et standalone, contrats de sorties composables et preuves de validation. Un formulaire simplifié ne limite pas le contrat du Tool.

Lire Docs/AutomaticInputs.md (AutomaticInputs.md depuis Docs) : chemins absolus acceptés pour les entrées locales, copie automatique privée par job, aucune copie manuelle exigée de l’IA.


## Task-owned files (SDK 0.9.0)

Read Docs/TaskFiles.md (TaskFiles.md from this Docs directory). Configure input roots and all file fields for automatic imports; AI sessions are temporary by default. FinishTask removes imported copies and generated workspaces after workers stop; export wanted results first. Standalone sessions explicitly use temporary=False.

## Modular CyUI maintenance

Read Docs/CyUIMigration.md before changing the standalone UI. The selected upstream
files in cyui.py and cyui_modules/ are unchanged and pinned/hash-checked by
cyui-source.json. Do not patch them in the application or reintroduce a private
palette/widget implementation. Refresh from the recorded checkout with
scripts/sync_cyui.py. Keep host adapters outside the library and import only used
families. Domain validation, decoding/rendering, jobs, persistence, task ownership
and Undo remain in this application. Preserve documented advanced-editor gaps and
all existing interactions. Run tests/test_modular_ui.py and the relevant native
UI tests; keep the root LICENCES/CyUI-MIT.txt and Options source attribution.
