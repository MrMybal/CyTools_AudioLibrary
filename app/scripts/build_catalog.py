"""Developer tool: regenerate app/models/catalog.json with pinned revisions, sizes and SHA-256.

Sizes and hashes are read from the Hugging Face API (LFS metadata) and from the GitHub
release of nttcslab/m2d at the moment this script runs; nothing is guessed. Run it with the
base runtime:  runtime/python/Scripts/python.exe app/scripts/build_catalog.py
"""
import json
import sys
import urllib.request
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
GIB = 1024**3
SMALL = ('config.json', 'generation_config.json', 'preprocessor_config.json', 'tokenizer.json', 'tokenizer_config.json', 'vocab.json',
         'vocab.txt', 'merges.txt', 'special_tokens_map.json', 'added_tokens.json', 'chat_template.json', 'chat_template.jinja',
         'model.safetensors.index.json', 'LICENSE')


def get(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'CyTools-AudioLibrary-catalog'})
    return json.load(urllib.request.urlopen(request, timeout=60))


def hf(repo, wanted, target='', revision=None):
    """Hugging Face block: files pinned to the current revision of `repo`, restricted to `wanted` names/predicates."""
    info = get(f'https://huggingface.co/api/models/{repo}?blobs=true')
    files = []
    for sibling in info['siblings']:
        name = sibling['rfilename']
        if not (name in wanted or any(callable(w) and w(name) for w in wanted)): continue
        lfs = sibling.get('lfs') or {}
        files.append({'path': name, 'size': sibling.get('size'), 'sha256': lfs.get('sha256', '')})
    card = info.get('cardData') or {}
    return {'kind': 'huggingface', 'repo': repo, 'revision': revision or info['sha'], 'target': target, 'files': files,
            'gated': bool(info.get('gated'))}, card


# Resources and similarity ranges below were measured on the validation machine (RTX 3090, data/reports/real-three-models.json):
# resident VRAM M2D 0.75 GiB, LAION-CLAP 0.6 GiB, Omni-Embed 3B 8.9 GiB (9.3 GiB peak); cosine of unrelated vs matching pairs.
def main():
    catalog = []
    releases = {r['tag_name']: r for r in get('https://api.github.com/repos/nttcslab/m2d/releases')}
    def m2d_asset(tag, name):
        asset = next(a for a in releases[tag]['assets'] if a['name'] == name)
        digest = (asset.get('digest') or '').removeprefix('sha256:')
        return {'kind': 'url-archive', 'url': asset['browser_download_url'], 'size': asset['size'], 'sha256': digest, 'archive': 'zip'}
    m2d_license = {'name': 'NTT Software License (see LICENSE.pdf); research use terms apply', 'url': 'https://github.com/nttcslab/m2d/blob/master/LICENSE.pdf',
                   'requiresAcceptance': True, 'notes': 'Read the PDF before use; this Tool does not grant any right on the weights.'}
    bert, _ = hf('google-bert/bert-base-uncased', ('config.json', 'tokenizer.json', 'tokenizer_config.json', 'vocab.txt'), 'support/google-bert/bert-base-uncased')
    catalog.append({
        'modelId': 'm2d-clap', 'version': '2025', 'revision': 'v0.5.0', 'displayName': 'M2D-CLAP 2025', 'family': 'M2D-CLAP',
        'modelType': 'AudioTextEmbedding', 'provider': 'NTT Communication Science Laboratories', 'repository': 'https://github.com/nttcslab/m2d',
        'source': m2d_asset('v0.5.0', 'm2d_clap_vit_base-80x1001p16x16p16kpBpTI-2025.zip'), 'auxiliary': [bert],
        'adapter': 'm2d_clap', 'engine': 'torch', 'engineSource': 'm2d', 'embeddingDimension': 768, 'requiredSampleRate': 16000,
        'maximumAudioDuration': None, 'preferredChunkDuration': 10.0, 'languages': ['en'],
        'capabilities': ['AudioEmbedding', 'TextEmbedding', 'ZeroShotTagging'], 'license': m2d_license,
        'resources': {'vramBytes': 2*GIB, 'ramBytes': 4*GIB}, 'similarityRange': [0.14, 0.36], 'defaultEnabled': True, 'flatFeatures': True,
        'validation': 'See Docs/AudioLibrary-Validation.md'})
    gte, _ = hf('thenlper/gte-base', ('config.json', 'tokenizer.json', 'tokenizer_config.json', 'vocab.txt', 'special_tokens_map.json', 'model.safetensors'), 'support/thenlper/gte-base')
    catalog.append({
        'modelId': 'm2d-clap', 'version': '2024', 'revision': 'v0.1.0', 'displayName': 'M2D-CLAP 2024', 'family': 'M2D-CLAP',
        'modelType': 'AudioTextEmbedding', 'provider': 'NTT Communication Science Laboratories', 'repository': 'https://github.com/nttcslab/m2d',
        'source': m2d_asset('v0.1.0', 'm2d_clap_vit_base-80x608p16x16-240128.zip'), 'auxiliary': [gte],
        'adapter': 'm2d_clap', 'engine': 'torch', 'engineSource': 'm2d', 'embeddingDimension': 768, 'requiredSampleRate': 16000,
        'maximumAudioDuration': None, 'preferredChunkDuration': 6.0, 'languages': ['en'],
        'capabilities': ['AudioEmbedding', 'TextEmbedding', 'ZeroShotTagging'], 'license': m2d_license,
        'resources': {'vramBytes': 3*GIB, 'ramBytes': 6*GIB}, 'similarityRange': [0.0, 0.5],
        'validation': 'Not validated on this machine: kept as the previous version of the same model family'})
    clap, card = hf('laion/clap-htsat-unfused', ('config.json', 'preprocessor_config.json', 'tokenizer.json', 'tokenizer_config.json', 'vocab.json',
                                               'merges.txt', 'special_tokens_map.json', 'pytorch_model.bin'))
    catalog.append({
        'modelId': 'laion-clap', 'version': 'htsat-unfused', 'revision': clap['revision'], 'displayName': 'LAION-CLAP (HTSAT unfused, legacy)',
        'family': 'CLAP', 'modelType': 'AudioTextEmbedding', 'provider': 'LAION', 'repository': 'https://huggingface.co/laion/clap-htsat-unfused',
        'source': clap, 'adapter': 'hf_clap', 'engine': 'torch', 'embeddingDimension': 512, 'requiredSampleRate': 48000,
        'maximumAudioDuration': 10.0, 'preferredChunkDuration': 10.0, 'languages': ['en'],
        'capabilities': ['AudioEmbedding', 'TextEmbedding', 'ZeroShotTagging'],
        'license': {'name': card.get('license', 'Not declared'), 'url': 'https://huggingface.co/laion/clap-htsat-unfused', 'requiresAcceptance': False},
        'resources': {'vramBytes': GIB+GIB//2, 'ramBytes': 3*GIB}, 'similarityRange': [0.05, 0.5], 'defaultEnabled': True})
    thinker = lambda name: name in ('model-00001-of-00003.safetensors', 'model-00002-of-00003.safetensors')
    for variant, repo, base, step, parameters, vram in (('qwen3b-cl', 'OEA-Qwen3B-Cl', 'Qwen/Qwen2.5-Omni-3B', 'step_40.pt', 3, 11),
                                                        ('qwen3b-ac', 'OEA-Qwen3B-AC', 'Qwen/Qwen2.5-Omni-3B', 'step_350.pt', 3, 11)):
        source, card = hf('JudeJiwoo/'+repo, (step,))
        backbone, base_card = hf(base, SMALL+(thinker,), 'backbone')
        backbone['thinkerOnly'] = True      # shard 3 holds only talker/token2wav weights, unused for embeddings
        catalog.append({
            'modelId': 'omni-embed-audio', 'version': variant, 'revision': source['revision'], 'displayName': 'Omni-Embed-Audio '+repo.split('-', 1)[1],
            'family': 'Omni-Embed-Audio', 'modelType': 'AudioTextEmbedding', 'provider': 'Omni-Embed-Audio authors (JudeJiwoo)',
            'repository': 'https://github.com/JudeJiwoo/Omni-Embed-Audio', 'source': source, 'auxiliary': [backbone], 'weightFile': step,
            'adapter': 'omni_embed', 'engine': 'torch', 'engineSource': 'Omni-Embed-Audio', 'embeddingDimension': 512, 'requiredSampleRate': 16000,
            'maximumAudioDuration': 128.0, 'preferredChunkDuration': 10.0, 'languages': ['multilingual backbone; trained on English captions'],
            'capabilities': ['AudioEmbedding', 'TextEmbedding', 'ZeroShotTagging'],
            'license': {'name': f"Checkpoint: {card.get('license', 'Not declared')}; backbone {base}: {base_card.get('license_name') or base_card.get('license')}",
                        'url': f'https://huggingface.co/{base}/blob/main/LICENSE', 'requiresAcceptance': True,
                        'notes': 'The backbone licence (Qwen Research for the 3B model) restricts commercial use; accept it personally before installing.'},
            'resources': {'vramBytes': vram*GIB, 'ramBytes': 16*GIB}, 'similarityRange': [0.05, 0.85], 'parameters': parameters, 'defaultDevice': 'cpu',
            'validation': 'See Docs/AudioLibrary-Validation.md' if variant == 'qwen3b-cl' else 'Not validated on this machine'})
    for identifier, repo, parameters, vram, default in (('qwen3-0.6b', 'Qwen/Qwen3-0.6B', 0.6, 2, False), ('qwen3-1.7b', 'Qwen/Qwen3-1.7B', 1.7, 5, True),
                                                        ('qwen3-4b', 'Qwen/Qwen3-4B', 4.0, 10, False)):
        source, card = hf(repo, SMALL+(lambda name: name.endswith('.safetensors'),))
        catalog.append({
            'modelId': identifier, 'version': '2025-04', 'revision': source['revision'], 'displayName': repo.split('/')[1], 'family': 'Qwen3',
            'modelType': 'LLM', 'provider': 'Alibaba Qwen', 'repository': 'https://huggingface.co/'+repo, 'source': source,
            'adapter': 'hf_causal_lm', 'engine': 'torch', 'parameters': parameters, 'defaultLlm': default,
            'capabilities': ['QueryUnderstanding', 'QueryExpansion', 'Translation', 'Classification', 'StructuredOutput'],
            'license': {'name': card.get('license', 'Not declared'), 'url': f'https://huggingface.co/{repo}/blob/main/LICENSE', 'requiresAcceptance': False},
            'resources': {'vramBytes': vram*GIB, 'ramBytes': int(parameters*4*GIB)+2*GIB}})
    flamingo, card = hf('nvidia/audio-flamingo-3-hf', ())
    catalog.append({
        'modelId': 'audio-flamingo-3', 'version': 'hf', 'revision': flamingo['revision'], 'displayName': 'Audio Flamingo 3 (declared, no adapter yet)',
        'family': 'Audio Flamingo', 'modelType': 'AudioUnderstanding', 'provider': 'NVIDIA', 'repository': 'https://github.com/NVIDIA/audio-flamingo',
        'adapter': '', 'engine': 'torch', 'maximumAudioDuration': 600.0, 'capabilities': ['Captioning', 'Reranking', 'QuestionAnswering'],
        'license': {'name': 'NVIDIA OneWay Noncommercial License (weights)', 'url': 'https://huggingface.co/nvidia/audio-flamingo-3-hf', 'requiresAcceptance': True},
        'resources': {'vramBytes': 20*GIB, 'ramBytes': 32*GIB},
        'validation': 'Extension point only: the registry, capabilities and Deep-mode hook exist, the adapter is not written or tested'})
    target = APP/'models'/'catalog.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(catalog, indent=1), encoding='utf-8')
    for entry in catalog:
        size = sum(f.get('size') or 0 for block in [entry.get('source') or {}]+entry.get('auxiliary', []) for f in (block.get('files') or [{'size': block.get('size')}]))
        print(f"{entry['modelId']}@{entry['version']}: {size/1e9:.2f} GB")


if __name__ == '__main__':
    sys.exit(main())
