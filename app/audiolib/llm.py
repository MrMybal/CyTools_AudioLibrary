"""Query understanding. The small LLM is optional and never the retrieval engine:
it rewrites a free-form request (any language) into a stable structured query that the
embedding models can use. Without an LLM, a deterministic parser produces the same shape.
"""
import json
import re
import time

from cytools_core import CyToolError

FIELDS = ('events', 'properties', 'environment', 'exclude', 'temporal', 'queries', 'categories', 'tags')
LIMITS = {'events': 6, 'properties': 6, 'environment': 4, 'exclude': 6, 'temporal': 6, 'queries': 4, 'categories': 4, 'tags': 10}
NEGATIONS = r"(?:without|with no|no|not|excluding|except|sans|pas de|pas d'|aucun|aucune|ohne|sin)"
STOPWORDS = set('''a an the of and or with in on at to for from by is are be this that these those very some any into over under
    sound sounds audio noise noises like such as then followed after before while during un une le la les des du de et ou avec dans sur
    pour par qui que ce cette ces tres très son sons bruit bruits puis'''.split())
SYSTEM = '''You convert a request for sound effects into a JSON search specification for an audio retrieval engine.
Answer with ONE JSON object only, no prose, no markdown. Always write the values in ENGLISH, whatever the language of the request.
Keys (all arrays of short lowercase strings):
- "events": sound events that must be heard, as short audio captions (e.g. "diesel engine starting").
- "properties": acoustic qualities (heavy, metallic, distant, long reverb, low frequency, muffled...).
- "environment": place or ambience if any (forest, warehouse, street...).
- "exclude": sounds the user does NOT want (music, birds, voices...). Empty if none.
- "temporal": the events in chronological order, only when the request describes a sequence; else empty.
- "queries": 2 or 3 natural English captions describing the wanted sound, from most literal to a paraphrase. Never mention excluded sounds in them.
Do not invent details that are not implied by the request.'''
EXAMPLES = [
    ("je veux un gros moteur diesel qui démarre puis tourne au ralenti sans musique",
     {"events": ["diesel engine cranking", "diesel engine starting", "engine idling"], "properties": ["heavy", "low frequency"],
      "environment": [], "exclude": ["music"], "temporal": ["diesel engine cranking", "diesel engine starting", "engine idling"],
      "queries": ["heavy diesel engine starting then idling", "large diesel motor cranking, starting and running at low idle"]}),
    ("forest ambience with wind but no birds",
     {"events": ["wind blowing through trees"], "properties": ["calm"], "environment": ["forest"], "exclude": ["birds", "birdsong"],
      "temporal": [], "queries": ["forest ambience with wind in the trees", "wind rustling leaves in a quiet forest"]}),
]


CAPTION_SYSTEM = (
    'You are a sound design search assistant. The user writes in any language, often informally, with typos, filler words '
    'or no grammar at all. Extract only the sound they want and answer with one JSON object holding clap_prompt, variations, '
    'suggested_categories, suggested_tags and exclude. clap_prompt and the three variations are clean English captions for a '
    'CLAP audio search engine and must describe only what the user asked for. suggested_categories and suggested_tags are '
    'generic sound library hints. exclude lists sounds the user does not want. Answer with the JSON object only.')
PROFILES = {
    # A model is never recognised by its name. It declares the prompt it was trained for in its registry entry
    # ("promptProfile"), so a different fine tune, or a second version of this one, needs no code change here.
    'generic': {'system': SYSTEM, 'examples': True, 'maxTokens': 400},
    'caption': {'system': CAPTION_SYSTEM, 'examples': False, 'maxTokens': 256},
}


def caption_schema(value):
    """Map a caption style answer (clap_prompt / variations / suggested_*) onto the internal structure.

    The captions become the queries sent to the embedding models, the suggested tags double as the concepts
    scored per result, and the suggested categories stay apart: they are only hints, and the search resolves
    them against whatever taxonomy the Library actually has.
    """
    variations = value.get('variations') or []
    if isinstance(variations, str): variations = [variations]
    tags = value.get('suggested_tags') or []
    return {'queries': [q for q in [value.get('clap_prompt')]+list(variations) if isinstance(q, str) and q.strip()],
            'events': [], 'properties': tags, 'environment': [], 'temporal': [],
            'categories': value.get('suggested_categories') or [], 'tags': tags, 'exclude': value.get('exclude') or []}


def has_negation(text):
    """True when the request negates something, in the languages the parser knows."""
    words = NEGATIONS[3:-1]+"|ne|non|nicht|kein|keine|never|jamais|hors"
    return bool(re.search(r"\b(?:"+words+r")\b", text, re.I) or re.search(r"\bn'", text, re.I))


def empty_query(text=''):
    return {'text': text, 'events': [], 'properties': [], 'environment': [], 'exclude': [], 'temporal': [],
            'queries': [text] if text else [], 'categories': [], 'tags': []}


def normalize(value, text):
    """Coerce any LLM output into the stable structure; unknown keys are dropped.

    Both answer shapes are accepted, so a Library can mix a general purpose LLM and a caption fine tune.
    """
    out = empty_query(text)
    if not isinstance(value, dict): return out
    if 'clap_prompt' in value: value = caption_schema(value)
    for field in FIELDS:
        items = value.get(field, [])
        if isinstance(items, str): items = [items]
        clean = []
        for item in items if isinstance(items, list) else []:
            if isinstance(item, str) and item.strip() and len(item) <= 160 and item.strip().lower() not in [c.lower() for c in clean]:
                clean.append(' '.join(item.split()))
        out[field] = clean[:LIMITS[field]]
    if not has_negation(text): out['exclude'] = []      # small LLMs copy exclusions from the examples; keep them only when the request negates something
    if not out['queries']: out['queries'] = [', '.join(out['events']) or text]
    excluded = [e.lower() for e in out['exclude']]
    out['queries'] = [q for q in out['queries'] if not any(re.search(r'\b'+re.escape(e)+r'\b', q.lower()) for e in excluded)] or out['queries'][:1]
    return out


def heuristic(text):
    """LLM-free parsing: negated fragments become exclusions, content words become concepts."""
    out = empty_query(text)
    pattern = re.compile(r'(?:,|\bbut\b|\bmais\b)?\s*\b'+NEGATIONS+r"\s+([^,.;]+?)(?=$|,|;|\.|\bbut\b|\bmais\b|\band\b|\bet\b)", re.I)
    positive = text
    for match in pattern.finditer(text):
        fragment = match.group(1).strip()
        if fragment: out['exclude'].append(fragment)
    positive = ' '.join(pattern.sub(' ', text).split()).strip(' ,;.') or text
    out['queries'] = [positive]
    words = [w for w in re.findall(r"[^\W\d_]{3,}", positive.lower()) if w not in STOPWORDS]
    out['properties'] = list(dict.fromkeys(words))[:LIMITS['properties']]
    sequence = re.split(r'\b(?:then|followed by|puis|suivi de|suivie de|suivi d\'|and then)\b', positive, flags=re.I)
    if len(sequence) > 1:
        out['temporal'] = [part.strip(' ,') for part in sequence if part.strip(' ,')][:LIMITS['temporal']]
        out['events'] = list(out['temporal'])
    out['exclude'] = out['exclude'][:LIMITS['exclude']]
    return out


def wants_llm(text):
    """Auto mode: a short plain English keyword query goes straight to the embedding models."""
    if len(text.split()) > 5: return True
    if re.search(r'[^\x00-\x7f]', text): return True
    if re.search(r'\b'+NEGATIONS+r'\b', text, re.I): return True
    return bool(re.search(r'\b(then|puis|suivi|followed|avec|qui|une?|des|les?|du)\b', text, re.I))


def extract_json(text):
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.S)
    start = text.find('{')
    if start < 0: raise ValueError('no JSON object in the answer')
    depth, in_string, escape = 0, False, False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape: escape = False
            elif char == '\\': escape = True
            elif char == '"': in_string = False
        elif char == '"': in_string = True
        elif char == '{': depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0: return json.loads(text[start:index+1])
    raise ValueError('unterminated JSON object')


def messages_for(text, profile='generic'):
    """A fine tune was trained on exactly one prompt: giving it the few shot examples of the generic
    prompt makes it answer worse, not better, so the profile decides both the system turn and the examples."""
    settings = PROFILES.get(profile) or PROFILES['generic']
    messages = [{'role': 'system', 'content': settings['system']}]
    if settings['examples']:
        for request, answer in EXAMPLES:
            messages += [{'role': 'user', 'content': request}, {'role': 'assistant', 'content': json.dumps(answer, ensure_ascii=False)}]
    return messages+[{'role': 'user', 'content': text}]


def pick_llm(registry, preferred='', configured=None):
    """The model to use: what the call asked for, else the one chosen in the application settings,
    else the catalogue default, else the smallest installed one.

    The settings step is what makes "default" mean the same thing in the interface, in the CLI and
    over MCP: an assistant that calls search_sounds without naming a model gets the user's choice,
    not a different model from the one they see on screen.
    """
    candidates = [d for d in registry.values() if d.is_llm and d.has('QueryUnderstanding') and d.installed and d.get('adapter')]
    if configured is None:
        from config import settings                  # read late: the setting can change between two searches
        configured = settings().get('llmModel', '')
    for wanted in (preferred, configured):
        for descriptor in candidates:
            if wanted and descriptor.key == wanted: return descriptor
    candidates.sort(key=lambda d: (d.get('parameters') or 0, d.key))
    for descriptor in candidates:
        if descriptor.get('defaultLlm'): return descriptor
    return candidates[0] if candidates else None


def understand(pool, registry, text, mode='auto', preferred='', device=None, cancelled=None):
    """-> (structured query, info). Never raises for an LLM problem: search continues with the parser."""
    info = {'mode': mode, 'used': False, 'modelKey': '', 'profile': '', 'seconds': 0.0, 'fallback': ''}
    if mode == 'off' or (mode == 'auto' and not wants_llm(text)): return heuristic(text), info
    descriptor = pick_llm(registry, preferred)
    if descriptor is None:
        info['fallback'] = 'No local LLM is installed; the built-in parser was used'
        return heuristic(text), info
    profile = descriptor.get('promptProfile') if descriptor.get('promptProfile') in PROFILES else 'generic'
    started = time.monotonic()
    try:
        answer = pool.host(descriptor).generate(descriptor, messages_for(text, profile), PROFILES[profile]['maxTokens'], device, cancelled)
        structured = normalize(extract_json(answer), text)
        info.update(used=True, modelKey=descriptor.key, profile=profile, seconds=round(time.monotonic()-started, 2))
        return structured, info
    except CyToolError as exc:
        if exc.code == 'Cancelled': raise
        info['fallback'] = exc.code+': '+exc.message
    except (ValueError, KeyError) as exc:
        info['fallback'] = 'Unusable LLM answer ('+str(exc)+'); the built-in parser was used'
    info.update(modelKey=descriptor.key, profile=profile, seconds=round(time.monotonic()-started, 2))
    return heuristic(text), info
