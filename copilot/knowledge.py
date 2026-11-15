"""Small, validated curriculum graph; standard library, no YAML dependency.

Front matter supports scalar strings and JSON-style string lists only. This is
an intentional YAML subset, not a general-purpose YAML parser.
"""
import json
import re
from pathlib import Path

from .content_checks import (STAGES, valid_steps, value_leak, verify_generated_hints, verify_generated_solution,
                             verify_generated_steps, words)  # noqa: F401 (words, STAGES re-exported)

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PROBLEMS = ROOT / 'data/sample_problems.jsonl'
GENERATED_MAX_BYTES = 8 * 1024 * 1024


def leaked(steps, answer_text):
    """True when a step's question, option or explanation contains the correct option value."""
    return any(value_leak(text, answer_text, numeric=False) for step in steps
               for text in [step['question'], step['why'], *step['options']])


def load_generated(path, container='problems', keyed_by_language=True):
    """Read one optional large-model file (D-013): {"version": 1, <container>: {...}}. Absent -> {}."""
    if path is None or not Path(path).is_file():
        return {}, {}
    path = Path(path)
    if path.stat().st_size > GENERATED_MAX_BYTES:
        raise ValueError(f'Generated content file is larger than {GENERATED_MAX_BYTES} bytes: {path}')
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError(f'Generated content file is not valid JSON: {path}: {error}') from error
    if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get(container), dict):
        raise ValueError(f'{path}: expected {{"version": 1, "{container}": {{...}}}}')
    items = data[container]
    if keyed_by_language:
        for key in items:
            pid, sep, language = key.rpartition('|')
            if not sep or not pid or not language:
                raise ValueError(f'{path}: keys must be "<id>|<language>", got {key!r}')
    meta = {k: data.get(k) for k in ('model', 'via', 'generated') if isinstance(data.get(k), str)}
    return items, meta


class Knowledge:
    def __init__(self, folder=ROOT / 'knowledge', annotations=None, generated_steps=None, generated_solutions=None,
                 generated_annotations=None):
        """`annotations` are human-reviewed files; the `generated_*` files are optional large-model
        content (knowledge/README.md, "Generated content"), re-verified per problem before use."""
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
        # Large-model content: never overrides a human entry; items are verified lazily per problem.
        self.generated_steps, self.steps_meta = load_generated(generated_steps)
        self.generated_solutions, self.solutions_meta = load_generated(generated_solutions)
        self.generated_tagged, self.generated_tags_dropped = set(), 0
        for path in [generated_annotations] if generated_annotations else []:
            items, _ = load_generated(path, keyed_by_language=False)
            for pid, item in items.items():
                if pid in self.annotations or not isinstance(item, dict) or item.get('status') != 'reviewed':
                    continue
                try:
                    self.validate_annotation(item)
                except ValueError:
                    self.generated_tags_dropped += 1  # e.g. a skill id that no longer exists
                    continue
                self.annotations[pid] = dict(item, generated=True)
                self.generated_tagged.add(pid)
        self._verified = {}
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
        valid_steps(steps, where)

    def verified(self, kind, problem):
        """The generated item of `kind` for this problem and language if it passes re-verification, else None.

        Results are memoised per (kind, id, language); make_handler warms the cache at startup."""
        key = f"{problem.get('id')}|{problem.get('language')}"
        memo = (kind, key)
        if memo not in self._verified:
            item, ok = None, False
            if kind == 'steps' and key in self.generated_steps:
                item = self.generated_steps[key]
                ok, _ = verify_generated_steps(item, problem)
            elif kind == 'solution' and key in self.generated_solutions:
                item = self.generated_solutions[key]
                ok, _ = verify_generated_solution(item, problem)
            elif kind == 'annotation':
                entry = self.annotations.get(problem.get('id'), {})
                if entry.get('generated') and entry.get('language', 'eng') == problem.get('language') and entry.get('hints'):
                    item = entry
                    ok, _ = verify_generated_hints(entry['hints'], problem)
            self._verified[memo] = (item, ok)
        item, ok = self._verified[memo]
        return item if ok else None

    def generated_report(self, problems):
        """Counts of generated items that match the loaded problems: served, dropped by re-verification."""
        report = {}
        for kind, source in (('steps', self.generated_steps), ('solution', self.generated_solutions), ('annotation', None)):
            loaded = dropped = 0
            for p in problems:
                key = f"{p.get('id')}|{p.get('language')}"
                entry = self.annotations.get(p.get('id'), {})
                present = (key in source) if source is not None else bool(
                    entry.get('generated') and entry.get('hints') and entry.get('language', 'eng') == p.get('language'))
                if present:
                    if self.verified(kind, p) is None:
                        dropped += 1
                    else:
                        loaded += 1
            report[kind] = {'loaded': loaded, 'dropped': dropped}
        report['tags'] = {'loaded': len(self.generated_tagged), 'dropped': self.generated_tags_dropped}
        return report

    def tag_source(self, problem):
        """'human', 'generated' or None for an untagged problem."""
        if not self.annotation(problem)['skills']:
            return None
        return 'generated' if problem.get('id') in self.generated_tagged else 'human'

    def thinking_steps(self, problem):
        """Return (steps, scope): reviewed problem steps, else verified generated steps, else skill steps, else none."""
        item = self.annotation(problem)
        steps = self.problem_steps.get(problem.get('id'), {}).get(problem.get('language'))
        if steps and item['skills']:
            return steps, 'problem'
        generated = self.verified('steps', problem)
        if generated:
            return generated, 'generated'
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
        """(hints, scope): human annotation, else verified generated ladder, else the skill's hints, else none."""
        item = self.annotation(problem)
        if not item.get('generated') and item.get('hints') and item.get('language', 'eng') == problem.get('language'):
            return item['hints'], 'problem'
        generated = self.verified('solution', problem) or self.verified('annotation', problem)
        if generated:
            return generated['hints'], 'generated'
        primary = item.get('assessment_skill')
        if primary:
            return self.skills[primary]['hints'], 'skill'
        return [], 'none'

    def solution(self, problem):
        """(text, scope): human annotation solution, else a verified generated one, else (None, 'none')."""
        item = self.annotation(problem)
        if not item.get('generated') and item.get('solution') and item.get('language', 'eng') == problem.get('language'):
            return item['solution'], 'problem'
        for generated in (self.verified('solution', problem), self.verified('annotation', problem)):
            if generated and isinstance(generated.get('solution'), str) and generated['solution'].strip():
                return generated['solution'], 'generated'
        return None, 'none'

    def public_graph(self):
        return [{'source': pre, 'target': sid, 'kind': 'supports_learning'}
                for sid, skill in self.skills.items() for pre in skill['prerequisites']]
