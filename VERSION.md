# CyTools AudioLibrary — version notes

[Français](VERSION.fr.md) · [README](README.md)

## Published application

**0.1.5 · EXPERIMENTAL · Windows x64**

This is the application version, not the version of its SDK or UI library. This experimental release is intended for evaluation.

- [Published release and checksums](https://github.com/MrMybal/CyTools_AudioLibrary/releases/tag/v0.1.5)
- [Portable Windows download](https://github.com/MrMybal/CyTools_AudioLibrary/releases/download/v0.1.5/CyTools_AudioLibrary-0.1.5-windows-x64.zip)

## Changes in this binary release

- Complete English/French CyDoc manual with navigation, search, contextual help and the relevant media.
- Offline reader and the existing native operation contracts retained.
- Python runtime ABI and model/engine requirements unchanged from the preceding application release.

The product showcase, README layout and repository navigation were added after this binary release. They do not announce a new executable or imply that later source changes shipped in the ZIP.

## Component versions

| Component | Version | Role |
| --- | --- | --- |
| CyTools AudioLibrary | 0.1.5 | Application |
| CyToolsCore | 0.10.1 | SDK / runtime |
| CyUI | 1.2.0 | Selected UI modules |
| CyDoc | 0.1.0 | Bundled reader |

## Documented limitations

Windows x64 is tested; the Linux launcher is unvalidated. Semantic search requires separately installed compatible models and the AI engine. Some model licences restrict commercial use. File Tools can rename files or write metadata only when explicitly requested.

Engines and weights are installed separately. A declared operation or a downloadable model is not evidence that every parameter combination, hardware configuration or model has been validated. Retain the licences delivered with your installed release.

## Bug reports and updates

The current release notes do not publish a bug-by-bug ticket list. Use the issue tracker for confirmed reports; the limitations above describe platform and optional-component availability.

- [Issue tracker](https://github.com/MrMybal/CyTools_AudioLibrary/issues)
- [All releases](https://github.com/MrMybal/CyTools_AudioLibrary/releases)

For a compatible existing installation, use its update stream and preserve data/models. A runtime ABI change requires its matching complete distribution; do not force an incompatible app-only update.
