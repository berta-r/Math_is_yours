"""Small, validated curriculum graph; standard library, no YAML dependency.

Front matter supports scalar strings and JSON-style string lists only. This is
an intentional YAML subset, not a general-purpose YAML parser.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGES = ('understand', 'plan', 'check')
SAMPLE_PROBLEMS = ROOT / 'data/sample_problems.jsonl'


def words(text):
    return len(text.split())


def leaked(steps, answer_text):
    """True when a step's question, option or explanation contains the correct option value."""
    value = (answer_text or '').strip()
    if not value:
        return False
    # Token boundaries: the value "5" is not leaked by "15", but "5 cm" or "is 5" is.
    pattern = re.compile(r'(?<!\w)' + re.escape(value) + r'(?!\w)', re.I)
    return any(pattern.search(text) for step in steps
               for text in [step['question'], step['why'], *step['options']])


class Knowledge:
    def __init__(self, folder=ROOT / 'knowledge', annotations=None):
        self.folder = Path(folder)
        self.skills = {}
        for path in sorted((self.folder / 'skills').glob('*.md')):
            raw = path.read_text(encoding='utf-8')
            parts = raw.split('---', 2)
            if len(parts) != 3 or parts[0].strip():
                raise ValueError(f'{path}: expected YAML front matter')
            meta = {}
            for line in parts[1].strip().splitlines():
                name, sep, value = line.partition(':')
                if not sep or name.strip() not in ('id', 'title', 'prerequisites'):
                    raise ValueError(f'{path}: unsupported metadata')
                meta[name.strip()] = json.loads(value) if value.strip().startswith('[') else value.strip()
            sid = meta.get('id', '')
            if not re.fullmatch(r'[a-z][a-z0-9_]*', sid) or sid in self.skills:
                raise ValueError(f'{path}: invalid or duplicate skill id')
            if not meta.get('title') or not isinstance(meta.get('prerequisites'), list):
                raise ValueError(f'{path}: title and prerequisite list required')
            body = parts[2].strip()
            sections = re.split(r'^## ', body, flags=re.M)
            meta['description'] = sections[0].strip()
            for section in sections[1:]:
                heading, _, content = section.partition('\n')
                meta[heading.strip().lower().replace(' ', '_')] = content.strip()
            meta['hints'] = [line[2:].strip() for line in meta.get('hints', '').splitlines() if line.startswith('- ')]
            if len(meta['hints']) != 3:
                raise ValueError(f'{path}: supply three authored hints')
            self.skills[sid] = meta
        if not self.skills:
            raise ValueError('No skills found')
        visiting, visited = set(), set()

        def depth(sid):
            if sid not in self.skills:
                raise ValueError(f'Unknown prerequisite: {sid}')
            if sid in visiting:
                raise ValueError(f'Prerequisite cycle at {sid}')
            if sid in visited:
                return self.skills[sid]['depth']
            visiting.add(sid)
            d = 1 + max((depth(p) for p in self.skills[sid]['prerequisites']), default=-1)
            visiting.remove(sid)
            visited.add(sid)
            self.skills[sid]['depth'] = d
            return d
        for sid in self.skills:
            depth(sid)
        self.model = json.loads((self.folder / 'model.json').read_text(encoding='utf-8'))
        for key in ('prior', 'guess', 'slip', 'learn', 'demonstrated_threshold'):
            if not 0 < self.model[key] < 1:
                raise ValueError(f'Invalid BKT parameter: {key}')
        if self.model['guess'] + self.model['slip'] >= 1:
            raise ValueError('Guess + slip must be less than 1')
        for key in ('min_evidence', 'min_successes'):
            if type(self.model[key]) is not int or self.model[key] < 1:
                raise ValueError(f'{key} must be a positive integer')
        if any(not isinstance(d, int) or d < 1 for d in self.model['review_days']) or not self.model['review_days']:
            raise ValueError('Review intervals must be positive days')
        self.diagnostics = json.loads((self.folder / 'diagnostics.json').read_text(encoding='utf-8'))
        self.annotations = {}
        self.load_thinking_steps(self.folder / 'thinking_steps.json')
        for path in [self.folder / 'sample_annotations.json', *(annotations or [])]:
            if Path(path).is_file():
                data = json.loads(Path(path).read_text(encoding='utf-8'))
                for pid, item in data['problems'].items():
                    if item.get('status') != 'reviewed':
                        continue
                    self.validate_annotation(item)
                    if 'thinking_steps' in item:
                        steps = item['thinking_steps']
                        self.validate_steps(steps, f'annotation {pid}')
                        self.problem_steps.setdefault(pid, {})[steps[0]['language']] = steps
                    self.annotations[pid] = item
        diagnostic_ids = set()
        for p in self.diagnostics:
            self.validate_annotation(p)
            if (p['id'] in diagnostic_ids or p['label'] not in list('ABCDE') or set(p['options']) != set('ABCDE')
                    or not p.get('text') or not p.get('language') or len(p.get('hints', [])) != 3
                    or len(p['skills']) != 1 or p.get('assessment_skill') != p['skills'][0]):
                raise ValueError(f'Invalid diagnostic: {p["id"]}')
            diagnostic_ids.add(p['id'])
            self.annotations[p['id']] = dict(p, status='reviewed', provenance='Original diagnostic')

    def load_thinking_steps(self, path):
        """Multiple-choice process questions; see knowledge/README.md, "Thinking steps"."""
        self.skill_steps, self.problem_steps = {}, {}
        if not Path(path).is_file():
            return
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        if not isinstance(data, dict) or not isinstance(data.get('skills'), dict) or not isinstance(data.get('problems', {}), dict):
            raise ValueError(f'{path}: expected "skills" and "problems" objects')
        for sid, steps in data['skills'].items():
            if sid not in self.skills:
                raise ValueError(f'Thinking steps for unknown skill: {sid}')
            self.validate_steps(steps, f'skill {sid}')
            if any(step['language'] != 'eng' for step in steps):
                raise ValueError(f'Thinking steps for skill {sid}: general steps must be in English')
            self.skill_steps[sid] = steps
        missing = sorted(set(self.skills) - set(self.skill_steps))
        if missing:
            raise ValueError(f'Thinking steps missing for skills: {", ".join(missing)}')
        references = {}
        if SAMPLE_PROBLEMS.is_file():
            for line in SAMPLE_PROBLEMS.read_text(encoding='utf-8').splitlines():
                if line.strip():
                    p = json.loads(line)
                    references[(p['id'], p['language'])] = p
        for pid, steps in data.get('problems', {}).items():
            self.validate_steps(steps, f'problem {pid}')
            reference = references.get((pid, steps[0]['language']))
            if reference and leaked(steps, reference['options'].get(reference.get('label'))):
                raise ValueError(f'Thinking steps for problem {pid} contain the correct option value')
            self.problem_steps.setdefault(pid, {})[steps[0]['language']] = steps
        everything = [step for steps in [*self.skill_steps.values(), *data.get('problems', {}).values()] for step in steps]
        for position in range(3):
            if sum(step['answer'] == position for step in everything) < .25 * len(everything):
                raise ValueError(f'Thinking-step answer position {position} is used in fewer than 25% of steps')

    @staticmethod
    def validate_steps(steps, where):
        if not isinstance(steps, list) or len(steps) != len(STAGES):
            raise ValueError(f'Thinking steps for {where}: expected exactly {len(STAGES)} steps')
        for expected, step in zip(STAGES, steps):
            if not isinstance(step, dict) or step.get('stage') != expected:
                raise ValueError(f'Thinking steps for {where}: stages must be {", ".join(STAGES)} in that order')
            label = f'Thinking step {where}/{expected}'
            for key in ('language', 'question', 'why'):
                if not isinstance(step.get(key), str) or not step[key].strip():
                    raise ValueError(f'{label}: {key} must be non-empty text')
            options = step.get('options')
            if not isinstance(options, list) or len(options) != 3 or any(not isinstance(o, str) or not o.strip() for o in options):
                raise ValueError(f'{label}: exactly three non-empty options are required')
            if len(set(o.strip().lower() for o in options)) != 3:
                raise ValueError(f'{label}: options must be distinct')
            if type(step.get('answer')) is not int or not 0 <= step['answer'] <= 2:
                raise ValueError(f'{label}: answer must be an integer from 0 to 2')
            counts = [words(o) for o in options]
            if max(counts) > 10 or max(counts) - min(counts) > 2:
                raise ValueError(f'{label}: options need at most 10 words and word counts within 2 of each other')
            if any(o.split()[0].strip(',.').lower() in ('all', 'none', 'both') for o in options):
                raise ValueError(f'{label}: options may not start with "All", "None" or "Both"')
            if words(step['question']) > 25 or words(step['why']) > 25:
                raise ValueError(f'{label}: question and why must be at most 25 words')
            why = step['why'].strip()
            if why[-1] not in '.!?' or re.search(r'[.!?]\s', why):
                raise ValueError(f'{label}: why must be exactly one sentence')
        if len({step['language'] for step in steps}) != 1:
            raise ValueError(f'Thinking steps for {where}: all steps need the same language')

    def thinking_steps(self, problem):
        """Return (steps, scope): reviewed problem steps, else the general skill steps, else none."""
        item = self.annotation(problem)
        steps = self.problem_steps.get(problem.get('id'), {}).get(problem.get('language'))
        if steps and item['skills']:
            return steps, 'problem'
        primary = item.get('assessment_skill') or (item['skills'][0] if item['skills'] else None)
        if primary and primary in self.skill_steps:
            return self.skill_steps[primary], 'skill'
        return [], 'none'

    def steps_skill(self, problem):
        item = self.annotation(problem)
        return item.get('assessment_skill') or (item['skills'][0] if item['skills'] else None)

    def validate_annotation(self, item):
        skills = item.get('skills')
        if not isinstance(skills, list) or not skills or len(skills) != len(set(skills)) or any(s not in self.skills for s in skills):
            raise ValueError('Annotations need distinct, known skills')
        primary = item.get('assessment_skill')
        if primary is not None and primary not in skills:
            raise ValueError('Assessment skill must be one of the tagged skills')
        hints = item.get('hints', [])
        if not isinstance(hints, list) or any(not isinstance(h, str) or not h.strip() for h in hints):
            raise ValueError('Hints must be a list of text strings')

    def annotation(self, problem):
        return self.annotations.get(problem['id'], {'skills': [], 'assessment_skill': None})

    def hints(self, problem):
        item = self.annotation(problem)
        if item.get('hints') and item.get('language', 'eng') == problem.get('language'):
            return item['hints'], 'problem'
        primary = item.get('assessment_skill')
        if primary:
            return self.skills[primary]['hints'], 'skill'
        return [], 'none'

    def public_graph(self):
        return [{'source': pre, 'target': sid, 'kind': 'supports_learning'}
                for sid, skill in self.skills.items() for pre in skill['prerequisites']]
