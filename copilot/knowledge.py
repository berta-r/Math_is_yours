"""Small, validated curriculum graph; standard library, no YAML dependency.

Front matter supports scalar strings and JSON-style string lists only. This is
an intentional YAML subset, not a general-purpose YAML parser.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
        for path in [self.folder / 'sample_annotations.json', *(annotations or [])]:
            if Path(path).is_file():
                data = json.loads(Path(path).read_text(encoding='utf-8'))
                for pid, item in data['problems'].items():
                    if item.get('status') != 'reviewed':
                        continue
                    self.validate_annotation(item)
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
