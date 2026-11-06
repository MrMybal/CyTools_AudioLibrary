---
id: guide-lisez-moi
title: User guide
description: Use the application step by step.
section: Guide
order: 10
parent: overview
revision: 31a03a357becd790
---

## CyTools_AudioLibrary {#cytools-audiolibrary}

Local intelligent audio library: management, analysis, categorization, and natural language search in large collections of sounds. Your files are never moved, copied, or modified (unless you use the Files tab yourself, see below): a reference library of folders, and everything that the Tool calculates (base, waveforms, embeddings, index) goes into a cache that you place wherever you want.

## Start {#demarrer}

0. Since a GitHub release: download `CyTools_AudioLibrary-<version>-windows-x64.zip`, extract it where the application is to live (it creates its private environment in this folder), then, only once, open PowerShell in the extracted folder and launch: `powershell -ExecutionPolicy Bypass -File app\Install.ps1` It requires Python 3.11 or later and git. The other two files from the release (`cytools-app.zip` and its `.sha256`) serve for the Updates tab: do not extract them manually.
1. Double-click on CyTools_AudioLibrary.exe (Linux: `./CyTools_AudioLibrary.sh`, not tested). If a message indicates that the private runtime is missing, it means step 0 was not done.
2. Installation Tab: install the AI engine (PyTorch private, several GB), then the desired models. The CySearchAssist-CLAP-1.5B assistant (1.6 GB, default) or its 0.5B version (0.5 GB, lighter) comes from Hugging Face, similar to CyMetaSound. For a model that requires a license, read it and check the acceptance box yourself: the Tool never accepts it on your behalf.
3. Library Tab : New library (name + cache folder, e.g. `G:\CyToolsCache\AudioLibrary`), Add a folder as many times as necessary, Rescan all.
4. Select the models to use (in the Models panel), then Analyze the library. The Analysis queue tab shows the progress and allows you to Pause / Resume / Cancel / Retry failed jobs.
5. Search in natural language, in any language: « large metallic impact with a long reverberation ». Click on a result: waveform, immediate playback, playhead, information, tags, categories, score for each model and corresponding segment.

## Your tags, categories, and notes on a sound, a selection, or a folder {#vos-tags-categories-et-notes-sur-un-son-une-selection-ou-un-dossier}

* A sound: Tags and categories tab under the waveform. Add or remove your tags, choose a category, then add the category or remove the category. You can also add a note from 0 to 5, a one-line description, and free-form notes. The description and notes are saved automatically without a button.
* Several sounds: Ctrl+click to add a sound to the selection, Shift+click to select an entire range, Ctrl+A to select all, Esc to clear. The tab becomes Selection (N) and every modification applies to all: tags (each tag already present shows how many sounds it applies to, and can be removed from all with a single click), category, note, favorite, a line added to the notes of each without deleting the existing ones, and Analyze these sounds.
* A folder: on the left panel, an arrow next to a folder opens its subfolders with the number of sounds they contain. A click displays this folder and everything it contains; right-click: Select all sounds in this folder, Analyze this folder, Open this folder. On a sound in the list, right-click > Show only this folder.

All of this stays in the library database: your audio files are unchanged. To rename files or write tags into them, open File tools and choose The selected sounds.

## Export sounds from the library: bundle and drag-and-drop {#sortir-des-sons-de-la-bibliotheque-bundle-et-glisser-deposer}

* Create a bundle: use the Selection tab or right-click a sound, choose Create a bundle…, then select a destination. Files are copied with a flat layout or their folders preserved. Originals are unchanged. Existing identical files are kept; a different file with the same name receives a numbered name. `bundle.json` records each file’s source, tags and categories; exporting again to the same destination updates the bundle. Disable `bundle.json` if you intend to import the whole folder into a game engine. Destinations inside a library or cache are rejected to prevent the exported copies from being indexed again.
* Drag-and-drop: drag a sound or selection out of the window, into Explorer to make copies, or into Unreal Engine's Content Browser to import them into the project. Only the copy is offered: a drag can never move or delete your originals.

## Automatic library updates {#mise-a-jour-automatique-des-bibliotheques}

By default, the application checks in the background (at startup and every 5 minutes) if files have been added, modified, or removed in your folders, and updates the library automatically, including the AI analysis of new sounds. Left panel > Automatic update: Automatically update, Ask me first (a banner appears with a button to Update now) or Disabled. Missing files are hidden, never deleted from the base: if they return or have been moved, they regain their tags.

## File tools (modify your files only at your request) {#outils-fichiers-modifient-vos-fichiers-uniquement-a-votre-demande}

* Rename misnamed files (`sound_01`, `ZOOM0012`...): the tool suggests a name based on the category and tags; you check, correct if needed, and confirm. Nothing is overwritten, and you can undo the last rename. Tags and analysis follow the file.
* Write tags into files (the audio equivalent of EXIF: ID3, Vorbis, MP4) so that other software can read them. The audio is verified to be identical before replacing the original, and a backup is kept in the cache.

## Appearance {#apparence}

Options tab: five themes (Medium gray, default, Light gray, Amber night, Purple, Blue ocean), compact or comfortable layout, and text size. The active filter, displayed folder, and selection appear as pills above the list: a click on the cross removes them. The bottom bar summarizes the library and ongoing tasks.

## Shortcuts {#raccourcis}

Space: play/pause · Up/Down: previous/next audio (Shift+Up/Down extends the selection) · Ctrl+click, Shift+click, Ctrl+A: multiple selection · Esc: clear selection · right-click on an audio: Find similar sounds · on the waveform: scroll wheel = zoom, Shift+scroll wheel = scroll, click = position, drag = select (then Loop the selection or Find similar sounds to the selection).

Click on a column header: sort the list by name, duration, type, category, tags, folder, analysis status, and, in search results, by final score or model score; a second click reverses the order. In results, a third click returns to the relevance order of the search. The selected sound remains selected when the order changes.

## Where are my data? {#ou-sont-mes-donnees}

| Folder | Content |
|---|---|
| `data/libraries` | portable definition of each library (folders, cache, models, taxonomy) |
| chosen cache (default `data/cache`) | base, waveforms, embeddings and index, by model and version |
| `data/models` | weights of installed models |
| `app/` | application files (replaced by updates) · `runtime/`: private Python, AI engine and staged updates |

Changing the model or version does not erase anything: the old data remains until you delete it (in the File Analysis tab). A reanalysis never deletes your tags or categories.
