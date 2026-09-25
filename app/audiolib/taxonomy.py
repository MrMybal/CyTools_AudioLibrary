"""Automatic categories and tags from stored embeddings (zero-shot, per model).

The taxonomy is data (hierarchical, editable, stored in the Library definition). Labelling
needs one text-embedding call per model and a matrix product over vectors already in the
cache: no audio file is decoded again. Only rows with source='auto' of that model are
replaced; user tags and user categories are never modified here.
"""
import numpy as np

from .database import replace_auto_labels
from .embeddings import EmbeddingStore
from .library import flatten_taxonomy

TEMPLATE = 'the sound of {}'


def categorize(library, database, pool, descriptor, audio_ids=None, device=None, cancelled=None, progress=None):
    store = EmbeddingStore.for_model(library, database, descriptor)
    if store is None or not descriptor.has('TextEmbedding'): return {'modelKey': descriptor.key, 'labelled': 0, 'skipped': 'Model has no text tower or no embeddings yet'}
    index = store.index()
    if not index.size: return {'modelKey': descriptor.key, 'labelled': 0}
    taxonomy, settings = library.taxonomy, library.settings
    nodes = flatten_taxonomy(taxonomy)
    tags = [t for t in dict.fromkeys(taxonomy.get('tags', [])) if t.strip()]
    prompts, owner = [], []
    for position, (_, _, _, texts) in enumerate(nodes):
        for text in texts: prompts.append(TEMPLATE.format(text)); owner.append(position)
    tag_offset = len(prompts)
    prompts += [TEMPLATE.format(tag) for tag in tags]
    if not prompts: return {'modelKey': descriptor.key, 'labelled': 0}
    vectors = pool.host(descriptor).embed_text(descriptor, prompts, device, cancelled)
    # one whole-clip row per asset: segment -1 when present, else the single window (rows are ordered by segment)
    rows = index.starts
    matrix = index.matrix[rows].astype(np.float32)
    vectors = vectors/np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-12)
    # Zero-shot classification as CLAP models are meant to be used: a softmax over the whole label set, so a score is a
    # probability *relative to the other labels*. An absolute cosine threshold labels everything (measured on real data).
    scale = float(descriptor.get('logitScale') or 40.0)
    wanted = None if audio_ids is None else set(audio_ids)
    labels, owner = {}, np.asarray(owner)
    node_columns = [np.flatnonzero(owner == position) for position in range(len(nodes))]
    def softmax(values):
        values = values-values.max(axis=1, keepdims=True); values = np.exp(values)
        return values/values.sum(axis=1, keepdims=True)
    for begin in range(0, len(rows), 8192):
        if cancelled and cancelled(): break
        similarities = matrix[begin:begin+8192] @ vectors.T
        category = softmax(scale*np.stack([similarities[:, columns].max(axis=1) for columns in node_columns], axis=1)) if nodes else np.zeros((len(similarities), 0))
        tagged = softmax(scale*similarities[:, tag_offset:]) if tags else np.zeros((len(similarities), 0))
        for offset in range(len(similarities)):
            audio_id = index.audio_ids[begin+offset]
            if wanted is not None and audio_id not in wanted: continue
            categories = {}
            for node in np.argsort(-category[offset])[:settings['categoriesPerFile']]:
                score = float(category[offset, node])
                if score < settings['categoryThreshold']: break
                categories[nodes[node][0]] = max(score, categories.get(nodes[node][0], 0))
                for parent in nodes[node][2]: categories[parent] = max(score, categories.get(parent, 0))     # a leaf implies its ancestors
            picked = [(tags[i], float(tagged[offset, i])) for i in np.argsort(-tagged[offset])[:settings['autoTagsPerFile']] if tagged[offset, i] >= settings['autoTagThreshold']]
            labels[audio_id] = {'categories': list(categories.items()), 'tags': picked}
        if progress: progress(100*min(len(rows), begin+8192)/len(rows))
    for begin in range(0, len(labels), 2000):
        chunk = dict(list(labels.items())[begin:begin+2000]); replace_auto_labels(database, descriptor.key, chunk)
    return {'modelKey': descriptor.key, 'labelled': len(labels), 'categories': len(nodes), 'tags': len(tags)}
