"""Query understanding accepts both answer shapes, and a suggestion never filters a Library.

No model is loaded here: these are the pure functions that sit between the LLM and the search, and the
point of the test is that a fine tune trained on another schema, or a category name that this Library
has never heard of, changes the ranking at most, never the set of results.

    runtime/python/Scripts/python.exe -m unittest discover -s app/tests -v
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audiolib import llm
from audiolib.search import resolve_hints

CAPTION_ANSWER = {
    'clap_prompt': 'A massive metallic impact in a large space',
    'variations': ['Huge steel hit with a long decay', 'Wide stereo capture of a metal impact', 'Heavy clang with resonant ringing'],
    'suggested_categories': ['Impacts', 'Metal impacts', 'Cartoon squeaks'],
    'suggested_tags': ['metal', 'impact', 'resonant'],
    'exclude': ['music'],
}
GENERIC_ANSWER = {
    'events': ['metal impact'], 'properties': ['heavy'], 'environment': ['warehouse'],
    'exclude': ['music'], 'temporal': [], 'queries': ['heavy metallic impact in a warehouse'],
}
TAXONOMY = {'categories': [{'id': 'impacts', 'name': 'Impacts', 'children': [{'id': 'impacts.metal', 'name': 'Metal impacts'}]}]}


class Library:
    taxonomy = TAXONOMY


class CaptionSchema(unittest.TestCase):
    def test_captions_become_the_queries(self):
        query = llm.normalize(CAPTION_ANSWER, 'gros impact metalik sans musique')
        self.assertEqual(query['queries'][0], CAPTION_ANSWER['clap_prompt'])
        self.assertEqual(len(query['queries']), 4)                      # the caption plus its three variations
        self.assertEqual(query['tags'], ['metal', 'impact', 'resonant'])
        self.assertEqual(query['categories'], ['Impacts', 'Metal impacts', 'Cartoon squeaks'])
        self.assertEqual(query['exclude'], ['music'])                   # the request does negate something

    def test_generic_answer_is_untouched(self):
        query = llm.normalize(GENERIC_ANSWER, 'heavy metal impact in a warehouse without music')
        self.assertEqual(query['queries'], GENERIC_ANSWER['queries'])
        self.assertEqual(query['events'], ['metal impact'])
        self.assertEqual(query['categories'], [])                       # the generic prompt suggests none

    def test_exclusions_need_a_negation_in_the_request(self):
        query = llm.normalize(CAPTION_ANSWER, 'gros impact metalik')    # nothing negated: the model invented it
        self.assertEqual(query['exclude'], [])

    def test_each_profile_has_its_own_prompt_and_no_leaked_examples(self):
        generic = llm.messages_for('boom', 'generic')
        caption = llm.messages_for('boom', 'caption')
        self.assertGreater(len(generic), len(caption))
        self.assertEqual(len(caption), 2)                               # system plus the raw request, nothing else
        self.assertIn('clap_prompt', caption[0]['content'])
        self.assertNotIn('clap_prompt', generic[0]['content'])
        self.assertEqual(llm.messages_for('boom', 'nonsense'), generic)  # an unknown profile falls back, it never raises

    def test_a_garbled_answer_still_produces_a_usable_query(self):
        """Never raise, and always leave at least one non-empty query to search with."""
        for broken in ({'clap_prompt': 42, 'variations': 'salvageable text'}, {'clap_prompt': '', 'variations': []},
                       {'clap_prompt': None, 'variations': None, 'suggested_tags': 'metal'}, {}, [], None, 'a string'):
            query = llm.normalize(broken, 'crash')
            self.assertTrue(query['queries'] and query['queries'][0].strip(), broken)
        # a broken caption falls back on the raw request, a usable variation is kept instead
        self.assertEqual(llm.normalize({'clap_prompt': '', 'variations': []}, 'crash')['queries'], ['crash'])
        self.assertEqual(llm.normalize({'clap_prompt': 42, 'variations': 'salvageable text'}, 'crash')['queries'], ['salvageable text'])


class Hints(unittest.TestCase):
    def test_only_categories_this_library_has_are_kept(self):
        hints = resolve_hints(Library(), llm.normalize(CAPTION_ANSWER, 'impact sans musique'))
        self.assertEqual(hints['categories'], ['impacts', 'impacts.metal'])
        self.assertEqual(hints['ignoredCategories'], ['Cartoon squeaks'])

    def test_matching_is_case_insensitive_and_accepts_identifiers(self):
        query = llm.empty_query('x'); query['categories'] = ['IMPACTS.METAL', 'impacts']
        self.assertEqual(resolve_hints(Library(), query)['categories'], ['impacts.metal', 'impacts'])

    def test_a_library_with_no_taxonomy_ignores_every_suggestion(self):
        class Bare: taxonomy = {'categories': []}
        hints = resolve_hints(Bare(), llm.normalize(CAPTION_ANSWER, 'impact'))
        self.assertEqual(hints['categories'], [])
        self.assertEqual(len(hints['ignoredCategories']), 3)             # reported, so the interface can say why


class Stub:
    """A Descriptor with the few members pick_llm touches, so no weights are needed."""
    def __init__(self, key, parameters=0, catalogue_default=False, installed=True):
        self.key, self.installed = key, installed
        self.data = {'parameters': parameters, 'defaultLlm': catalogue_default, 'adapter': 'hf_causal_lm'}
    is_llm = True
    def has(self, *_): return True
    def get(self, name, default=None): return self.data.get(name, default)


class DefaultModel(unittest.TestCase):
    """One default for the interface, the CLI and MCP: whatever the settings name."""
    def setUp(self):
        self.registry = {d.key: d for d in (Stub('small@1', 600_000_000), Stub('catalogue@1', 1_700_000_000, catalogue_default=True),
                                            Stub('fine-tune@1'), Stub('absent@1', installed=False))}

    def test_the_configured_model_wins_over_the_catalogue_default(self):
        self.assertEqual(llm.pick_llm(self.registry, configured='fine-tune@1').key, 'fine-tune@1')

    def test_an_explicit_request_still_wins_over_the_configured_one(self):
        self.assertEqual(llm.pick_llm(self.registry, preferred='small@1', configured='fine-tune@1').key, 'small@1')

    def test_no_configuration_falls_back_to_the_catalogue_default(self):
        self.assertEqual(llm.pick_llm(self.registry, configured='').key, 'catalogue@1')

    def test_a_configured_model_that_is_gone_does_not_break_the_search(self):
        self.assertEqual(llm.pick_llm(self.registry, configured='absent@1').key, 'catalogue@1')
        self.assertEqual(llm.pick_llm(self.registry, configured='deleted@9').key, 'catalogue@1')
        self.assertIsNone(llm.pick_llm({}, configured='fine-tune@1'))


class TrainedModelAnswers(unittest.TestCase):
    """The answers the fine tune actually produced, replayed through the parsing path."""
    SAMPLES = Path(__file__).resolve().parents[1]/'tests'/'fixtures'/'caption_answers.json'

    def test_every_recorded_answer_parses(self):
        if not self.SAMPLES.is_file(): self.skipTest('no recorded answers in this checkout')
        for record in json.loads(self.SAMPLES.read_text(encoding='utf-8')):
            query = llm.normalize(llm.extract_json(record['answer']), record['query'])
            self.assertTrue(query['queries'][0], record['query'])
            self.assertLessEqual(len(query['queries']), 4)
            self.assertTrue(all(isinstance(t, str) for t in query['tags']))


if __name__ == '__main__':
    unittest.main()
