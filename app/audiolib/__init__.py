"""Business layer of CyTools_AudioLibrary: no ImGui, no PyTorch, no model import.

Model descriptor + capability + analysis output + index provider are the four concepts the
rest of the package is written around; no module branches on the name of a model.
"""
# Audio only: video containers (.mp4, .mov...) are deliberately excluded, a Library is a sound library.
AUDIO_EXTENSIONS = ('.wav', '.flac', '.mp3', '.ogg', '.oga', '.opus', '.m4a', '.aac',
                    '.aif', '.aiff', '.aifc', '.wv', '.wma', '.caf', '.w64', '.au')
