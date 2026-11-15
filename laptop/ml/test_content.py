"""Tests for verify_content.py and the generator's parsing/retry. Standard library only, no model.

    .venv-ml/bin/python -m unittest laptop.ml.test_content

Not tested here: the model-dependent path (LlamaBackend, ServerBackend against a
real llama-server, ApiBackend against the real hosted API) and the quality of
generated text.
"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import generate_content as gen  # noqa: E402
from verify_content import letter_leak, value_leak, verify_explanation, verify_skills, verify_solution, verify_steps  # noqa: E402
from copilot.knowledge import Knowledge  # noqa: E402

PROBLEM = {'id': 'p1', 'language': 'eng', 'text': 'Anna has 3 bags with 4 apples in each bag. She eats 2 apples. How many are left?',
           'options': {'A': '8', 'B': '9', 'C': '10', 'D': '12', 'E': '14'}, 'label': 'C', 'text_only': True}
PROBLEM_CAT = dict(PROBLEM, language='cat', text="L'Anna té 3 bosses amb 4 pomes a cada bossa. Se'n menja 2. Quantes en queden?")

STEPS = [
    {'stage': 'understand', 'language': 'eng', 'question': 'What does the question ask you to find?',
     'options': ['How many apples are in each bag', 'How many apples Anna has at the end', 'How many apples Anna ate in total'],
     'answer': 1, 'why': 'The question asks how many are left, which is the amount after Anna eats some apples.'},
    {'stage': 'plan', 'language': 'eng', 'question': 'Which first move is most useful?',
     'options': ['Find how many apples are in the bags', 'Add the numbers three, four and two', 'Take two away from the four apples'],
     'answer': 0, 'why': 'You need the starting total of apples before you can take away the ones Anna eats.'},
    {'stage': 'check', 'language': 'eng', 'question': 'Which check fits your final answer?',
     'options': ['It is bigger than the total in the bags', 'It equals the number of apples in one bag', 'It is less than the total in the bags'],
     'answer': 2, 'why': 'Anna eats some apples, so she must end with fewer apples than were in the bags at the start.'},
]


def mutate(path, value, steps=STEPS):
    out = copy.deepcopy(steps)
    i, key = path[:2]
    if len(path) == 3:
        out[i][key][path[2]] = value
    else:
        out[i][key] = value
    return out


class ExplanationRules(unittest.TestCase):
    def ok(self, item, problem=PROBLEM, label='A'):
        return verify_explanation(item, problem, label)

    def test_good_english(self):
        item = {'explanation': 'That number could come from adding 4 and 4. Think about what happens to the apples in every bag.',
                'question': 'How many apples are there before Anna eats any?'}
        self.assertEqual(self.ok(item), (True, []))

    def test_good_catalan(self):
        item = {'explanation': 'Aquest nombre podria sortir de sumar 4 i 4. Pensa en les pomes de cada bossa.',
                'question': 'Quantes pomes hi ha abans que se les mengi?'}
        self.assertEqual(self.ok(item, PROBLEM_CAT), (True, []))

    def test_value_leak_whole_number_only(self):
        item = {'explanation': 'The answer should be 10 apples.', 'question': 'How many are left?'}
        self.assertIn('leak:value', self.ok(item)[1])
        item = {'explanation': 'That could come from adding 100 and 4.', 'question': 'How many are left?'}
        self.assertNotIn('leak:value', self.ok(item)[1])  # 10 inside 100 is not a leak

    def test_value_leak_decimal_comma(self):
        problem = dict(PROBLEM_CAT, options=dict(PROBLEM['options'], C='2,5'))
        self.assertTrue(value_leak('el resultat és 2,5 metres', problem))
        self.assertTrue(value_leak('the result is 2.5 m', problem))
        self.assertFalse(value_leak('2 and 5', problem))

    def test_letter_leak(self):
        for text in ('The answer is C.', 'Pick (C) now.', 'It is letter C', 'La resposta és C', 'C) is right', 'Option C wins'):
            self.assertTrue(letter_leak(text, 'C'), text)
        self.assertFalse(letter_leak('Count each bag.', 'C'))
        # "A" is an English article: only explicit patterns count.
        self.assertFalse(letter_leak('A bag has four apples. Answer a question first.', 'A'))
        self.assertTrue(letter_leak('The answer is A.', 'A'))
        self.assertTrue(letter_leak('Choose (A).', 'A'))

    def test_lengths(self):
        item = {'explanation': ' '.join(['word'] * 41) + '.', 'question': 'What do you see?'}
        self.assertIn('length:explanation_words', self.ok(item)[1])
        item = {'explanation': 'You added. Then you added. Then you added again.', 'question': 'What do you see?'}
        self.assertIn('length:explanation_sentences', self.ok(item)[1])
        item = {'explanation': 'You added the numbers.', 'question': ' '.join(['what'] * 21) + '?'}
        self.assertIn('length:question_words', self.ok(item)[1])
        item = {'explanation': 'You added the numbers.', 'question': 'Look at the bags.'}
        self.assertIn('format:question_mark', self.ok(item)[1])

    def test_language(self):
        english_in_cat = {'explanation': 'That is what you get by adding the numbers.', 'question': 'What is in each bag?'}
        self.assertIn('language:english_words_in_cat', self.ok(english_in_cat, PROBLEM_CAT)[1])
        catalan_in_eng = {'explanation': 'Aquest nombre surt de sumar els nombres.', 'question': 'Què hi ha a cada bossa?'}
        reasons = self.ok(catalan_in_eng)[1]
        self.assertIn('language:catalan_words_in_eng', reasons)

    def test_voice(self):
        item = {'explanation': 'I think you added the numbers.', 'question': 'What is in each bag?'}
        self.assertIn('voice:first_person', self.ok(item)[1])
        item = {'explanation': 'As an AI, the number could come from adding.', 'question': 'What is in each bag?'}
        self.assertIn('voice:as_an_ai', self.ok(item)[1])
        # Catalan "I" at the start of a sentence means "and": not first person.
        item = {'explanation': 'Has sumat els nombres. I després has restat.', 'question': 'Què hi ha a cada bossa?'}
        self.assertNotIn('voice:first_person', self.ok(item, PROBLEM_CAT)[1])

    def test_empty_and_correct_label(self):
        self.assertEqual(self.ok({'explanation': '', 'question': 'Why?'})[1], ['format:empty_explanation'])
        good = {'explanation': 'That could come from adding the numbers.', 'question': 'What is in each bag?'}
        self.assertIn('format:label_is_correct', self.ok(good, label='C')[1])


class StepRules(unittest.TestCase):
    def test_reference_steps_pass_and_match_knowledge(self):
        self.assertEqual(verify_steps(STEPS, PROBLEM), (True, []))
        Knowledge.validate_steps(STEPS, 'test')  # the bank's own validator agrees

    def assert_bank_rejects(self, steps, reason):
        ok, reasons = verify_steps(steps, PROBLEM)
        self.assertFalse(ok)
        self.assertIn(reason, reasons)
        with self.assertRaises(ValueError):
            Knowledge.validate_steps(steps, 'test')

    def test_stage_order(self):
        self.assert_bank_rejects([STEPS[1], STEPS[0], STEPS[2]], 'format:stage_order')

    def test_option_rules(self):
        self.assert_bank_rejects(mutate((0, 'options', 0), 'How many apples Anna has at the end'), 'options:not_distinct')
        self.assert_bank_rejects(mutate((0, 'options', 0), 'Bags'), 'options:word_count_spread')
        self.assert_bank_rejects(mutate((0, 'options', 0), 'All of the apples in the bag'), 'options:all_none_both')
        self.assert_bank_rejects(mutate((0, 'options'), ['a'] * 1 + ['b c'] * 0 + ['x'] * 0), 'format:three_options')
        long = ' '.join(['apples'] * 11)
        steps = mutate((0, 'options'), [long, long + ' x', long + ' y z'])
        self.assert_bank_rejects(steps, 'length:option_words')

    def test_question_why_rules(self):
        self.assert_bank_rejects(mutate((1, 'question'), ' '.join(['what'] * 26) + '?'), 'length:question_words')
        self.assert_bank_rejects(mutate((1, 'why'), ' '.join(['because'] * 26) + '.'), 'length:why_words')
        self.assert_bank_rejects(mutate((1, 'why'), 'First this. Then that.'), 'format:why_one_sentence')
        self.assert_bank_rejects(mutate((1, 'why'), 'No full stop'), 'format:why_one_sentence')
        self.assert_bank_rejects(mutate((1, 'answer'), 3), 'format:answer_index')

    def test_leaks(self):
        ok, reasons = verify_steps(mutate((2, 'why'), 'Anna must end with 10 apples left.'), PROBLEM)
        self.assertIn('leak:value', reasons)
        ok, reasons = verify_steps(mutate((2, 'options', 0), 'The answer is C for sure'), PROBLEM)
        self.assertIn('leak:letter', reasons)

    def test_language_and_voice(self):
        cat = [dict(s, language='cat') for s in STEPS]
        self.assertIn('language:english_words_in_cat', verify_steps(cat, PROBLEM_CAT)[1])
        self.assertIn('format:language_field', verify_steps(cat, PROBLEM)[1])
        self.assertIn('voice:first_person', verify_steps(mutate((0, 'question'), 'What do I need to find?'), PROBLEM)[1])


class FakeBackend:
    """Replays canned replies and records the messages it was sent."""
    name = 'fake'

    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def chat(self, messages, max_tokens, schema=None):
        self.calls.append(messages)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def model_steps(steps=STEPS):
    return {'steps': [{'stage': s['stage'], 'question': s['question'], 'correct': s['options'][s['answer']],
                       'wrong': [o for i, o in enumerate(s['options']) if i != s['answer']], 'why': s['why']} for s in steps]}


class Parsing(unittest.TestCase):
    def test_parse_json_variants(self):
        self.assertEqual(gen.parse_json('{"a": 1}'), {'a': 1})
        self.assertEqual(gen.parse_json('```json\n{"a": 1}\n```'), {'a': 1})
        self.assertEqual(gen.parse_json('<think>hmm {"b": 2}</think>\nSure: {"a": 1} done'), {'a': 1})
        self.assertIsNone(gen.parse_json('no json here'))
        self.assertIsNone(gen.parse_json('[1, 2]'))
        self.assertIsNone(gen.parse_json(None))

    def test_retry_once_with_stricter_instruction(self):
        backend = FakeBackend(['not json', '{"explanation": "x", "question": "y?"}'])
        value, raw, tries = gen.ask(backend, [{'role': 'system', 'content': 'S'}, {'role': 'user', 'content': 'U'}],
                                    50, None, gen.explanation_shape)
        self.assertEqual((value['explanation'], tries), ('x', 2))
        self.assertTrue(backend.calls[1][0]['content'].endswith(gen.STRICT))
        self.assertEqual(backend.calls[0][0]['content'], 'S')

    def test_skip_after_two_failures(self):
        backend = FakeBackend(['{"wrong": 1}', OSError('down')])
        value, raw, tries = gen.ask(backend, [{'role': 'system', 'content': 'S'}], 50, None, gen.explanation_shape)
        self.assertIsNone(value)
        self.assertEqual(len(backend.calls), 2)

    def test_build_steps_rotation(self):
        for position in range(3):
            steps = gen.build_steps(model_steps(), 'eng', position)
            self.assertEqual([s['answer'] for s in steps], [(position + i) % 3 for i in range(3)])
            for built, ref in zip(steps, STEPS):
                self.assertEqual(built['options'][built['answer']], ref['options'][ref['answer']])
            Knowledge.validate_steps(steps, 'built')

    def test_copied_example_detected(self):
        self.assertTrue(gen.copied_example(STEPS))  # STEPS is the prompt example itself


class SolutionAndSkillRules(unittest.TestCase):
    GOOD = {'solution': 'There are 3 bags of 4 apples, so 12 apples. Anna eats 2. So she has 10 apples left.',
            'hints': ['Look at how many apples are in each bag.', 'First find the total, then take away what she eats.',
                      'You have the total of 12. What happens when 2 are eaten?']}

    def test_good_solution(self):
        self.assertEqual(verify_solution(self.GOOD, PROBLEM), (True, []))

    def test_solution_rules(self):
        bad = dict(self.GOOD, solution='There are 12 apples and she eats 2.')
        self.assertIn('solution:missing_correct_value', verify_solution(bad, PROBLEM)[1])
        bad = dict(self.GOOD, solution='So 10 apples remain. That is because 12 minus 2.')
        self.assertIn('solution:value_not_at_end', verify_solution(bad, PROBLEM)[1])
        bad = dict(self.GOOD, solution=' '.join(['apples'] * 90) + ' 10.')
        self.assertIn('length:solution_words', verify_solution(bad, PROBLEM)[1])

    def test_hint_rules(self):
        bad = dict(self.GOOD, hints=['The result is 10.', *self.GOOD['hints'][1:]])
        self.assertIn('leak:value_in_hint', verify_solution(bad, PROBLEM)[1])
        bad = dict(self.GOOD, hints=['Look at option B first.', *self.GOOD['hints'][1:]])
        self.assertIn('leak:letter_in_hint', verify_solution(bad, PROBLEM)[1])
        bad = dict(self.GOOD, hints=[' '.join(['look'] * 21), *self.GOOD['hints'][1:]])
        self.assertIn('length:hint_words', verify_solution(bad, PROBLEM)[1])
        self.assertEqual(verify_solution(dict(self.GOOD, hints=['a', 'b']), PROBLEM), (False, ['format:three_hints']))
        self.assertIn('language:english_words_in_cat', verify_solution(self.GOOD, PROBLEM_CAT)[1])

    def test_skills(self):
        known = {'arithmetic', 'patterns', 'division'}
        self.assertEqual(verify_skills({'skills': ['arithmetic'], 'assessment_skill': 'arithmetic', 'confidence': .8}, known), (True, []))
        self.assertTrue(verify_skills({'skills': ['arithmetic', 'patterns'], 'assessment_skill': None, 'confidence': 1}, known)[0])
        self.assertIn('skills:unknown_id', verify_skills({'skills': ['algebra'], 'assessment_skill': None, 'confidence': .5}, known)[1])
        self.assertIn('skills:assessment_not_in_skills',
                      verify_skills({'skills': ['arithmetic'], 'assessment_skill': 'patterns', 'confidence': .5}, known)[1])
        self.assertIn('skills:confidence', verify_skills({'skills': ['arithmetic'], 'assessment_skill': None, 'confidence': 2}, known)[1])
        self.assertEqual(verify_skills({'skills': [], 'assessment_skill': None, 'confidence': .5}, known)[1], ['skills:count'])
        self.assertEqual(verify_skills({'skills': list(known) + ['x'], 'assessment_skill': None, 'confidence': .5}, known)[1], ['skills:count'])


class ApiBackendRetries(unittest.TestCase):
    """ApiBackend with a fake HTTP function and a fake sleep: no network."""

    def make(self, responses):
        calls, sleeps = [], []

        def http(url, body, headers, timeout):
            calls.append(json.loads(body))
            self.assertTrue(headers['Authorization'].startswith('Bearer '))
            reply = responses.pop(0)
            if isinstance(reply, Exception):
                raise reply
            return reply
        backend = gen.ApiBackend('https://api.example.test/v1', 'secret-key', 'main-model', 'fallback-model',
                                 http=http, sleep=sleeps.append, backoff=1.0)
        return backend, calls, sleeps

    @staticmethod
    def ok(content='{"a": 1}', tokens=7):
        return 200, {}, json.dumps({'choices': [{'message': {'content': content, 'reasoning_content': 'ignored'}}],
                                    'usage': {'prompt_tokens': tokens, 'completion_tokens': 3, 'total_tokens': tokens + 3}}).encode()

    def test_body_and_usage(self):
        backend, calls, _ = self.make([self.ok()])
        self.assertEqual(backend.chat([{'role': 'user', 'content': 'x'}], 100), '{"a": 1}')
        body = calls[0]
        self.assertEqual((body['model'], body['temperature'], body['max_tokens'], body['reasoning_effort'], body['response_format']),
                         ('main-model', 0, 600, 'low', {'type': 'json_object'}))
        self.assertEqual((backend.usage['total_tokens'], backend.usage['requests']), (10, 1))
        self.assertNotIn('secret-key', repr(backend))

    def test_429_honours_retry_after_then_backoff(self):
        backend, calls, sleeps = self.make([(429, {'Retry-After': '7'}, b''), (429, {}, b''), (429, {}, b''), self.ok()])
        self.assertEqual(backend.chat([], 10), '{"a": 1}')
        self.assertEqual(sleeps, [7.0, 2.0, 4.0])  # Retry-After first, then backoff * 2**retries
        self.assertEqual(backend.usage['rate_limited'], 3)
        self.assertEqual({c['model'] for c in calls}, {'main-model'})

    def test_gives_up_after_five_retries(self):
        backend, calls, sleeps = self.make([(429, {}, b'')] * 6)
        with self.assertRaises(OSError):
            backend.chat([], 10)
        self.assertEqual((len(calls), len(sleeps)), (6, 5))

    def test_fallback_on_5xx_and_no_access(self):
        backend, calls, _ = self.make([(503, {}, b'busy'), self.ok()])
        backend.chat([], 10)
        self.assertEqual([c['model'] for c in calls], ['main-model', 'fallback-model'])
        self.assertEqual(backend.usage['fallback_requests'], 1)
        backend, calls, _ = self.make([(401, {}, b'{"error": "Key does not have access to this model"}'), self.ok()])
        backend.chat([], 10)
        self.assertEqual([c['model'] for c in calls], ['main-model', 'fallback-model'])

    def test_other_errors_raise(self):
        backend, calls, _ = self.make([(401, {}, b'bad key')])
        with self.assertRaises(OSError):
            backend.chat([], 10)
        self.assertEqual(len(calls), 1)

    def test_network_error_retries(self):
        backend, calls, sleeps = self.make([OSError('reset'), self.ok()])
        self.assertEqual(backend.chat([], 10), '{"a": 1}')
        self.assertEqual(sleeps, [1.0])

    def test_key_from_env_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / '.env.local'
            path.write_text('OTHER=1\nTEST_CONTENT_KEY="abc"\n')
            import os
            os.environ.pop('TEST_CONTENT_KEY', None)
            self.assertEqual(gen.load_api_key('TEST_CONTENT_KEY', path), 'abc')


class Runs(unittest.TestCase):
    """End-to-end runs with the fake backend: files written, rejects recorded, resume skips."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.args = type('A', (), dict(explanations_out=d / 'e.json', steps_out=d / 's.json', rejects_out=d / 'r.json',
                                       solutions_out=d / 'sol.json', skills_out=d / 'sk.json',
                                       annotations_out=d / 'teaching_annotations.generated.json',
                                       resume=False, limit=None, show=0, text_only=False, workers=1, save_every=50))()
        self.rows = [dict(PROBLEM, _split='train'), dict(PROBLEM_CAT, _split='train')]

    def tearDown(self):
        self.tmp.cleanup()

    def backend(self, replies):
        b = FakeBackend(replies)
        b.via = 'fake'
        return b

    def test_steps_run_accepts_rejects_and_resumes(self):
        steps = copy.deepcopy(STEPS)
        steps[0]['options'][1] = 'How many apples remain for Anna'
        steps[0]['why'] = 'Think about the bags and how many apples each one holds.'
        steps[1]['options'][0] = 'Work out the apples inside the bags'
        steps[1]['why'] = 'You need the total first.'
        steps[2]['options'] = ['It is bigger than the bag total', 'It equals one bag of apples', 'It is smaller than the bag total']
        steps[2]['why'] = 'Eating apples leaves fewer.'
        for step in steps:  # nothing may equal the prompt's worked example
            step['options'] = ['Here: ' + o for o in step['options']]
        backend = self.backend([json.dumps(model_steps(steps)), 'garbage', 'still garbage'])
        stats, _ = gen.run_kind(gen.Steps(self.args), backend, self.rows, self.args)
        self.assertEqual((stats['accepted'], stats['unparsed']), (1, 1), stats)
        saved = json.loads(self.args.steps_out.read_text())
        self.assertEqual(list(saved['problems']), ['p1|eng'])
        rejects = json.loads(self.args.rejects_out.read_text())['steps']
        self.assertEqual(rejects['p1|cat']['reasons'], ['parse:failed'])
        self.args.resume = True
        stats, _ = gen.run_kind(gen.Steps(self.args), self.backend([]), self.rows, self.args)
        self.assertEqual(stats['tasks'], 0)

    def test_skills_and_solutions_make_loadable_annotations(self):
        rows = [dict(PROBLEM, id='sample-1', _split='train')]
        gen.run_kind(gen.Skills(self.args), self.backend(['{"skills": ["arithmetic", "multiplication"], '
                                                          '"assessment_skill": "arithmetic", "confidence": 0.9}']), rows, self.args)
        gen.run_kind(gen.Solutions(self.args), self.backend([json.dumps(SolutionAndSkillRules.GOOD)]), rows, self.args)
        report = gen.write_annotations(self.args, self.backend([]))
        self.assertEqual(report['check'], 'loads with copilot.knowledge.Knowledge')
        data = json.loads(self.args.annotations_out.read_text())['problems']['sample-1']
        self.assertEqual((data['status'], data['language'], data['skills'][0]), ('reviewed', 'eng', 'arithmetic'))
        self.assertEqual(data['hints'], SolutionAndSkillRules.GOOD['hints'])

    def test_refuses_reviewed_annotations_file(self):
        self.args.annotations_out = gen.ROOT / 'data/teaching_annotations.json'
        with self.assertRaises(SystemExit):
            gen.write_annotations(self.args, self.backend([]))


if __name__ == '__main__':
    unittest.main()
