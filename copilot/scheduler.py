"""Deterministic, explainable practice recommendations; prerequisites are advice.

With a difficulty table and an ability theta (T-103), candidates that pass the
existing rules are ranked by how close their predicted success is to TARGET
(about 70%), before the level tie-breaker.
"""
from .difficulty import probability
from .student_model import states, utc_now

TARGET = 0.7
DIFFICULTY_REASON = {
    'eng': 'Chosen so that you have about a 70% chance: your rating is {theta:.2f} and this problem\'s difficulty is {b:.2f}.',
    'cat': "Triat perquè tinguis prop d'un 70% de probabilitats d'encert: la teva puntuació és {theta:.2f} i la dificultat d'aquest problema és {b:.2f}.",
}


def recommend(con, student, catalog, knowledge, focus=None, language='eng', skill_id=None, now=None, preferred_kind=None, prefer_assessment=False,
              difficulty=None, theta=None):
    now = now or utc_now()
    targeted = difficulty is not None and theta is not None
    state = states(con, student, knowledge, now)
    if skill_id and skill_id not in state:
        raise ValueError('Unknown skill')
    # Canonical ids: translated copies do not count as unseen exercises.
    seen = {r[0].split('|')[0] for r in con.execute(
        'SELECT problem FROM sessions WHERE student=? AND (tries>0 OR hints>0 OR revealed>0)', (student,))}
    choices = {}
    for key, p in catalog.problems.items():
        if p.get('label') not in list('ABCDE'):
            continue
        if p.get('text_only') is False and not catalog.image(key):
            continue
        existing = choices.get(p['id'])
        rank = (p['language'] != language, p['language'] != 'eng', key)
        if not existing or rank < existing[0]:
            choices[p['id']] = (rank, key, p)
    entries = [(key, p) for _, key, p in choices.values()]
    entries.sort(key=lambda pair: pair[0])
    focus_key = None
    if focus:
        session = con.execute('SELECT * FROM sessions WHERE id=? AND student=?', (focus, student)).fetchone()
        if session:
            focus_key = session['return_to'] or session['problem']
    focus_problem = catalog.problems.get(focus_key, {})
    focus_tags = knowledge.annotation(focus_problem).get('skills', []) if focus_problem else []

    def pick(sid, kind=None, allow_repeat=False, exclude=None, assessment=False):
        candidates = []
        for key, p in entries:
            tag = knowledge.annotation(p)
            if sid not in tag['skills'] or (kind and p.get('kind', 'exercise') != kind):
                continue
            if assessment and tag.get('assessment_skill') != sid:
                continue
            if p['id'] == exclude or (not allow_repeat and p['id'] in seen):
                continue
            gap = abs(probability(theta, difficulty.b(p['id'], p.get('level'))) - TARGET) if targeted else 0.0
            candidates.append((p['id'] in seen, tag.get('assessment_skill') != sid,
                               p['language'] != language, gap, int(p.get('level') or 0), key, p))
        return min(candidates, key=lambda c: c[:-1])[-2:] if candidates else None

    def result(pair, sid, reason, kind, return_to=None):
        key, p = pair
        out = {'problem': key, 'id': p['id'], 'language': p['language'], 'skill_id': sid,
               'skill': knowledge.skills[sid]['title'], 'reason': reason, 'kind': kind,
               'return_to': return_to, 'fresh': p['id'] not in seen,
               'language_fallback': p['language'] != language}
        if targeted:
            b = difficulty.b(p['id'], p.get('level'))
            sentence = DIFFICULTY_REASON.get(p['language'], DIFFICULTY_REASON['eng']).format(theta=theta, b=b)
            out.update(p_success=round(probability(theta, b), 2), b=round(b, 4), difficulty_reason=sentence,
                       reason=reason + ' ' + sentence)
        return out

    # A user-selected node is always available, regardless of prerequisites.
    if skill_id:
        pair = None
        if prefer_assessment:
            pair = (pick(skill_id, preferred_kind, assessment=True) if preferred_kind else None) or pick(skill_id, 'exercise', assessment=True) or pick(skill_id, 'diagnostic', assessment=True)
        pair = pair or pick(skill_id, 'exercise') or pick(skill_id, 'diagnostic') or pick(skill_id, allow_repeat=True)
        if pair:
            return result(pair, skill_id, f"You chose to practise {state[skill_id]['name']}.", 'chosen')

    # First diagnose the focus skill, then any likely supporting gap. No cascade.
    if focus_tags:
        targets = sorted(focus_tags, key=lambda sid: (state[sid]['evidence'] > 0, state[sid]['mastery'], sid))
        for sid in targets:
            row = state[sid]
            if row['evidence'] == 0:
                pair = pick(sid, 'diagnostic')
                if pair:
                    return result(pair, sid, f"A short check will help us understand {row['name']} before choosing your next exercise.", 'diagnostic', focus_key)
            if row['evidence'] and row['mastery'] < .65:
                for pre in knowledge.skills[sid]['prerequisites']:
                    support = state[pre]
                    if support['evidence'] == 0 or support['mastery'] < .65:
                        pair = pick(pre, 'diagnostic') if support['evidence'] == 0 else pick(pre, 'exercise') or pick(pre, 'diagnostic')
                        if pair:
                            return result(pair, pre, f"Let's check {support['name']}, which supports {row['name']}. Your recent work suggests this is worth checking.", 'prerequisite', focus_key)
                pair = pick(sid, 'exercise') or pick(sid, 'diagnostic')
                if pair:
                    return result(pair, sid, f"Practise {row['name']} in a different problem to build more independent evidence.", 'repair', focus_key)

    for row in sorted(state.values(), key=lambda s: (s['next_review'] or '9999', s['id'])):
        if row['due']:
            sid = row['id']
            pair = pick(sid, 'exercise') or pick(sid, 'diagnostic') or pick(sid, allow_repeat=True)
            if pair:
                return result(pair, sid, f"{row['name']} is due for review. Your previous mastery evidence has been kept.", 'review')

    if focus_tags:
        for sid in focus_tags:
            pair = pick(sid, 'exercise', exclude=focus_problem.get('id')) or pick(sid, 'diagnostic', exclude=focus_problem.get('id'))
            if pair:
                return result(pair, sid, f"Try {state[sid]['name']} in a new situation to see what carries over.", 'transfer')

    total = sum(s['evidence'] for s in state.values())
    # Occasional stretch is a suggestion, never a prerequisite lock.
    if total and total % 5 == 0:
        for sid, row in state.items():
            if row['prerequisites'] and any(state[p]['evidence'] for p in row['prerequisites']):
                pair = pick(sid, 'exercise') or pick(sid, 'diagnostic')
                if pair:
                    return result(pair, sid, f"A stretch opportunity in {row['name']}. Hints are available, and you can choose another skill.", 'stretch')
    ordered = sorted(state.values(), key=lambda s: (s['evidence'] == 0, s['mastery'], s['depth'], s['id']))
    for row in ordered:
        sid = row['id']
        if row['state'] == 'demonstrated':
            continue
        pair = pick(sid, 'diagnostic') if row['evidence'] == 0 else pick(sid, 'exercise') or pick(sid, 'diagnostic')
        if pair:
            return result(pair, sid, f"{'Start with a short check of' if not row['evidence'] else 'Build more evidence for'} {row['name']}.", 'diagnostic' if not row['evidence'] else 'practice')
    return {'problem': None, 'reason': 'No fresh tagged problems remain. Choose any exercise for extra practice, or return for a scheduled review.', 'kind': 'complete'}
