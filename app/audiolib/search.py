"""Multi-model retrieval with rank fusion.

Every enabled model retrieves independently from its own index with its own query vectors.
Embeddings of different models are never added or compared. The final order comes from
weighted Reciprocal Rank Fusion:  FinalScore(asset) = sum_m  weight_m / (K + rank_m(asset)).
Percentages shown next to a result are a calibrated display of each model's cosine
similarity (descriptor.similarityRange); they explain a rank, they do not produce it.
"""
import time

import numpy as np

from cytools_core import CyToolError
from . import llm
from .database import build_filter, fetch_rows
from .embeddings import EmbeddingStore
from .library import flatten_taxonomy
from .registry import get_model


def resolve_hints(library, structured):
    """What the query understanding suggested, kept only where it exists in THIS Library.

    A caption model proposes category and tag names from general sound library practice. It has never
    seen the user's taxonomy, so a name it invents must not filter anything out. Names that match a
    category of this Library, by id or by name, become a small re-ordering bonus; the rest are reported
    as ignored so the interface can show what was dropped and why.
    """
    known = {}
    for identifier, name, _, _ in flatten_taxonomy(library.taxonomy):
        known[identifier.lower()] = identifier
        known[name.lower()] = identifier
    matched, ignored = [], []
    for suggestion in structured.get('categories', []):
        found = known.get(suggestion.strip().lower())
        (matched.append(found) if found else ignored.append(suggestion))
    return {'categories': list(dict.fromkeys(matched)), 'ignoredCategories': ignored,
            'tags': [t.strip().lower() for t in structured.get('tags', []) if t.strip()][:10]}


def calibrate(similarity, bounds):
    low, high = bounds
    return float(np.clip((similarity-low)/max(1e-6, high-low), 0.0, 1.0))


def resolve_models(library, registry, requested=None, capability=('AudioEmbedding',)):
    keys = list(requested) if requested else library.enabled_models
    models = []
    for key in keys:
        descriptor = get_model(key, registry)
        if descriptor.has(*capability): models.append(descriptor)
    return models


def _allowed_mask(database, index, filters):
    if not filters: return None
    where, values = build_filter(filters)
    allowed = {row[0] for row in database.query('SELECT a.audio_id FROM assets a'+where, values)}
    return np.fromiter((audio_id in allowed for audio_id in index.audio_ids), bool, len(index.audio_ids))


def search(library, database, pool, registry, *, text='', similar_to='', selection=None, models=None, filters=None, top_k=50,
           llm_mode='auto', llm_model='', weights=None, rrf_k=60, device=None, cancelled=None, understood=None):
    started = time.monotonic()
    text = (text or '').strip()
    if not text and not similar_to: raise CyToolError('InvalidParameters', 'Provide a text query or similarTo')
    mode = 'text' if text else ('selection' if selection else 'similar')
    descriptors = resolve_models(library, registry, models, ('AudioEmbedding', 'TextEmbedding') if mode == 'text' else ('AudioEmbedding',))
    if not descriptors:
        raise CyToolError('InvalidState', 'No embedding model is enabled for this Library', recoverable=True,
                          suggested_action='Enable an installed model for the Library, then run analyze_library')
    # `understood` lets a caller that searches several Libraries run the LLM once for the same request
    structured, llm_info = understood or (llm.understand(pool, registry, text, llm_mode, llm_model, device, cancelled) if mode == 'text'
                                          else (llm.empty_query(), {'mode': 'off', 'used': False}))
    source = None
    if mode != 'text':
        source = database.asset(similar_to)
        if not source: raise CyToolError('NotFound', 'Unknown asset: '+str(similar_to))
    settings = library.settings
    weights = {**settings.get('modelWeights', {}), **(weights or {})}
    positives = list(dict.fromkeys(structured['queries']+structured['events']))[:7]
    negatives = structured['exclude'][:4]
    concepts = list(dict.fromkeys(structured['events']+structured['properties']+structured['environment']))[:10]
    ordered = structured['temporal'] if len(structured['temporal']) > 1 else []
    per_model, reports, fused, candidates = {}, [], {}, max(200, top_k*4)
    for descriptor in descriptors:
        if cancelled and cancelled(): raise CyToolError('Cancelled', 'Search cancelled')
        report = {'modelKey': descriptor.key, 'displayName': descriptor['displayName'], 'searched': 0, 'seconds': 0.0, 'skipped': ''}
        reports.append(report); began = time.monotonic()
        store = EmbeddingStore.for_model(library, database, descriptor)
        if store is None: report['skipped'] = 'Not analyzed yet with the installed version of this model'; continue
        index = store.index()
        if not index.size: report['skipped'] = 'No embeddings in this store'; continue
        report.update(analysisKey=store.key, searched=index.size, assets=len(index.audio_ids))
        host = pool.host(descriptor)
        if mode == 'text':
            texts = positives+negatives+concepts+ordered
            vectors = host.embed_text(descriptor, texts, device, cancelled)
            bounds = descriptor.get('similarityRange') or [0.0, 0.5]
        else:
            if mode == 'selection':
                vectors = host.embed_selection(descriptor, source['absolute_path'], selection[0], selection[1], device, cancelled)
            else:
                rows, vectors = store.asset_vectors(similar_to)
                if not len(vectors): report['skipped'] = 'The reference sound is not analyzed with this model'; continue
                vectors = vectors[:1]       # whole-clip vector (segment -1) or the single window
            bounds = descriptor.get('audioSimilarityRange') or [0.3, 1.0]
        similarities = index.similarities(vectors)
        if mode == 'text':
            count = len(positives)
            row_score = 0.5*similarities[:, 0]+0.5*similarities[:, :count].max(axis=1)
            excluded = None
            if negatives:
                excluded = similarities[:, count:count+len(negatives)].max(axis=1)
                row_score = row_score-settings['excludePenalty']*np.maximum(0.0, excluded-np.median(excluded))
        else: row_score, excluded = similarities[:, 0], None
        asset_score, asset_row = index.per_asset(row_score)
        mask = _allowed_mask(database, index, filters)
        valid = np.ones(len(asset_score), bool) if mask is None else mask
        if mode != 'text' and similar_to in index.position and mode == 'similar': valid[index.position[similar_to]] = False
        order = np.argsort(-np.where(valid, asset_score, -np.inf))[:min(candidates, int(valid.sum()))]
        weight = float(weights.get(descriptor.key, 1.0))
        for rank, position in enumerate(order, 1):
            audio_id = index.audio_ids[position]
            fused[audio_id] = fused.get(audio_id, 0.0)+weight/(rrf_k+rank)
        per_model[descriptor.key] = {'index': index, 'score': asset_score, 'row': asset_row, 'similarities': similarities,
                                     'ranks': {index.audio_ids[p]: r for r, p in enumerate(order, 1)}, 'bounds': bounds, 'weight': weight,
                                     'excluded': excluded, 'conceptOffset': len(positives)+len(negatives), 'orderedOffset': len(positives)+len(negatives)+len(concepts)}
        report['seconds'] = round(time.monotonic()-began, 3)
    if not per_model:
        raise CyToolError('NotAnalyzed', 'None of the selected models has embeddings for this Library: '
                          + '; '.join(f"{r['modelKey']}: {r['skipped']}" for r in reports), recoverable=True,
                          suggested_action='Run analyze_library for these models, then search again')
    hints = resolve_hints(library, structured) if mode == 'text' else {'categories': [], 'ignoredCategories': [], 'tags': []}
    order = sorted(fused.items(), key=lambda item: -item[1])
    boosted = 0
    if hints['categories'] or hints['tags']:
        # Applied to the candidates fusion already found, never as a filter: a hint can be wrong, and a
        # file the embeddings ranked first must still be able to stay first.
        strength = float(settings.get('hintBoost', 0.12))
        window = order[:max(top_k*3, 60)]
        known = fetch_rows(database, [audio_id for audio_id, _ in window])
        wanted, tagged = set(hints['categories']), set(hints['tags'])
        rescored = []
        for audio_id, score in window:
            row = known.get(audio_id) or {}
            categories = len(wanted & set(row.get('categories', [])))
            tags = len(tagged & {t.lower() for t in row.get('autoTags', [])+row.get('userTags', [])})
            bonus = (1.0+strength)**min(categories, 2)*(1.0+strength/2)**min(tags, 3)
            boosted += bonus > 1.0
            rescored.append((audio_id, score*bonus))
        order = sorted(rescored, key=lambda item: -item[1])+order[len(window):]
    ranking = order[:top_k]
    rows = fetch_rows(database, [audio_id for audio_id, _ in ranking])
    best_possible = sum(m['weight']/(rrf_k+1) for m in per_model.values()) or 1.0
    results = []
    for audio_id, rrf in ranking:
        asset = rows.get(audio_id)
        if not asset: continue
        models_out, best = {}, None
        for key, data in per_model.items():
            index = data['index']; position = index.position.get(audio_id)
            if position is None: continue
            row = int(data['row'][position]); similarity = float(data['score'][position])
            entry = {'score': round(100*calibrate(similarity, data['bounds']), 1), 'similarity': round(similarity, 4),
                     'rank': data['ranks'].get(audio_id), 'segment': {'index': int(index.segment[row]), 'start': float(index.start[row]), 'stop': float(index.stop[row])}}
            if data['excluded'] is not None: entry['excludedSimilarity'] = round(float(data['excluded'][row]), 4)
            if concepts:
                offset = data['conceptOffset']
                scored = [(concepts[i], calibrate(float(data['similarities'][row, offset+i]), data['bounds'])) for i in range(len(concepts))]
                entry['concepts'] = [{'concept': c, 'score': round(100*s, 1)} for c, s in sorted(scored, key=lambda x: -x[1]) if s >= 0.35][:6]
            if ordered:
                begin = int(index.starts[position]); end = int(index.starts[position+1]) if position+1 < len(index.starts) else index.size
                windows = [r for r in range(begin, end) if index.segment[r] >= 0]
                if len(windows) > 1:
                    block = data['similarities'][windows, data['orderedOffset']:data['orderedOffset']+len(ordered)]
                    times = [float(index.start[windows[int(i)]]) for i in block.argmax(axis=0)]
                    entry['temporal'] = {'events': ordered, 'times': times, 'inOrder': all(a <= b for a, b in zip(times, times[1:]))}
            models_out[key] = entry
            if best is None or entry['score']*data['weight'] > best[1]: best = (key, entry['score']*data['weight'])
        total = sum(per_model[k]['weight'] for k in models_out) or 1.0
        final = sum(models_out[k]['score']*per_model[k]['weight'] for k in models_out)/total
        result = {'audioId': audio_id, 'filename': asset['filename'], 'path': asset['absolute_path'], 'duration': asset['duration'],
                  'finalScore': round(final, 1), 'rrf': round(rrf, 6), 'rrfNormalized': round(rrf/best_possible, 4), 'models': models_out,
                  'categories': asset['categories'], 'userTags': asset['userTags'], 'autoTags': asset['autoTags']}
        if best:
            segment = models_out[best[0]]['segment']
            if segment['index'] >= 0 and (asset['duration'] or 0) > segment['stop']-segment['start']+0.5:
                result['matchedSegment'] = {**segment, 'modelKey': best[0]}
            if models_out[best[0]].get('concepts'): result['matchedConcepts'] = models_out[best[0]]['concepts']
        results.append(result)
    return {'mode': mode, 'query': {'text': text, 'structured': structured if mode == 'text' else None, 'llm': llm_info,
                                    'hints': {**hints, 'boostedCandidates': boosted} if mode == 'text' else None,
                                    'similarTo': similar_to or None, 'selection': list(selection) if selection else None},
            'fusion': {'method': 'ReciprocalRankFusion', 'k': rrf_k, 'weights': {k: v['weight'] for k, v in per_model.items()}},
            'models': reports, 'results': results, 'total': len(fused), 'seconds': round(time.monotonic()-started, 3)}
