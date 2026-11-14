"""Small offline relation graph and evidence-based study paths.

Relatedness is a visual/exploration aid. Only authored prerequisite edges can
justify a supporting-skill step; no relationship changes a student's estimate.
"""
import json
import math
from pathlib import Path

from .knowledge import ROOT


class LearningGraph:
    def __init__(self, knowledge, artifact=None):
        candidate = Path(artifact) if artifact is not None else ROOT / 'data/skill_graph.json'
        if not candidate.is_file():
            candidate = knowledge.folder / 'relations.json'
        self.related_edges = []
        self.method = 'prerequisites-only'
        self.metadata = {}
        if not candidate.is_file():
            return
        if candidate.stat().st_size > 262144:
            raise ValueError('Skill graph exceeds the 256 KiB runtime budget')
        try:
            data = json.loads(candidate.read_text(encoding='utf-8'))
        except (UnicodeError, json.JSONDecodeError) as error:
            raise ValueError(f'Invalid skill graph: {candidate}') from error
        self.related_edges = validate_relations(data, knowledge.skills)
        self.method = data['method']
        self.metadata = {key: data[key] for key in ('version', 'method', 'source', 'source_digest') if key in data}


def validate_relations(data, skills):
    if not isinstance(data, dict) or data.get('version') != 1:
        raise ValueError('Skill graph needs version 1 metadata')
    if data.get('method') not in ('embeddings', 'keyword-tfidf', 'reviewed'):
        raise ValueError('Unknown skill graph method')
    ids = data.get('skill_ids')
    if not isinstance(ids, list) or any(not isinstance(s, str) for s in ids) or len(ids) != len(set(ids)) or set(ids) != set(skills):
        raise ValueError('Skill graph does not match the current curriculum; rebuild it on the laptop')
    edges = data.get('related_edges')
    if not isinstance(edges, list) or len(edges) > min(len(skills) * 5, len(skills) * (len(skills)-1)//2):
        raise ValueError('Skill graph has too many related edges')
    clean, seen = [], set()
    for edge in edges:
        if not isinstance(edge, dict):
            raise ValueError('Related edge must be an object')
        source, target, weight = edge.get('source'), edge.get('target'), edge.get('weight')
        if (not isinstance(source, str) or not isinstance(target, str) or source not in skills or target not in skills
                or source == target or edge.get('kind') != 'semantic'):
            raise ValueError('Related edges need two different known skills and semantic kind')
        if type(weight) not in (int, float) or not math.isfinite(weight) or not 0 < weight <= 1:
            raise ValueError('Related-edge weights must be finite and in (0, 1]')
        pair = tuple(sorted((source, target)))
        if pair in seen:
            raise ValueError('Duplicate undirected skill relation')
        seen.add(pair)
        clean.append({'source':pair[0], 'target':pair[1], 'weight':round(weight, 6), 'kind':'semantic'})
    return sorted(clean, key=lambda edge: (edge['source'], edge['target']))


def build_path(states, knowledge, goal=None, related_edges=None):
    """Return up to six next steps; unknown evidence is never called weakness.

    A demonstrated prerequisite supports a goal without forcing the student to
    redo all of its ancestors. Relatedness only breaks ties for exploration when
    there is no observed need; it cannot add an invented prerequisite.
    """
    if set(states) != set(knowledge.skills):
        raise ValueError('Student states must cover the curriculum')
    if goal is not None and goal not in knowledge.skills:
        raise ValueError('Unknown learning goal')
    strengths = [sid for sid in sorted(states) if states[sid]['state'] == 'demonstrated']
    if goal is None:
        developing = [sid for sid in states if states[sid]['state'] == 'developing']
        due = [sid for sid in states if states[sid].get('due')]
        if developing:
            goal = min(developing, key=lambda sid: (states[sid]['mastery'], knowledge.skills[sid]['depth'], sid))
        elif due:
            goal = min(due, key=lambda sid: (states[sid].get('next_review') or '', sid))
        else:
            unknown = [sid for sid in states if states[sid]['state'] == 'not_assessed']
            candidates = unknown or sorted(states)
            similarity = {sid:0.0 for sid in candidates}
            for edge in related_edges or []:
                a, b = edge['source'], edge['target']
                if a in strengths and b in similarity:
                    similarity[b] = max(similarity[b], edge['weight'])
                if b in strengths and a in similarity:
                    similarity[a] = max(similarity[a], edge['weight'])
            goal = min(candidates, key=lambda sid: (-similarity[sid], knowledge.skills[sid]['depth'], sid))
    ordered, visited, supports = [], set(), set()

    def visit(sid):
        if sid in visited:
            return
        visited.add(sid)
        row = states[sid]
        if row['state'] == 'demonstrated':
            if sid != goal and not row.get('due'):
                supports.add(sid)
            else:
                ordered.append(sid)
            return
        parents = knowledge.skills[sid]['prerequisites']
        parents = sorted(parents, key=lambda pre: (states[pre]['state'] != 'developing', states[pre]['mastery'], pre))
        for pre in parents:
            visit(pre)
        ordered.append(sid)

    visit(goal)
    steps = []
    for sid in ordered[:6]:
        row = states[sid]
        name = knowledge.skills[sid]['title']
        role = 'goal' if sid == goal else 'support'
        if row.get('due'):
            reason = f'Revisit {name}; its review date is due, while its previous evidence is retained.'
        elif row['state'] == 'not_assessed':
            reason = f'Start with a short check of {name}; we do not yet have independent evidence.'
        elif row['state'] == 'developing':
            reason = f'Build independent evidence for {name} with a new problem and a written first idea.'
        else:
            reason = f'Apply your demonstrated understanding of {name} in a new situation.'
        steps.append({'id':sid, 'name':name, 'state':row['state'], 'role':role, 'reason':reason, 'due':bool(row.get('due'))})
    name = knowledge.skills[goal]['title']
    reason = f'A suggested route toward {name}, using your independent evidence and the authored prerequisite links.'
    if supports:
        reason += ' Builds on demonstrated ' + ', '.join(knowledge.skills[sid]['title'] for sid in sorted(supports)) + '.'
    if len(ordered) > 6:
        reason += f' The next six of {len(ordered)} steps are shown.'
    return {'goal':goal, 'goal_name':name, 'steps':steps, 'reason':reason,
            'next_skill':steps[0]['id'] if steps else goal,
            'strengths':[{'id':sid, 'name':knowledge.skills[sid]['title']} for sid in sorted(supports)],
            'remaining_steps':max(0, len(ordered)-6)}
