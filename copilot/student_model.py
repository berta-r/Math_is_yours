"""Provisional BKT and separate review dates. No model fitting or network calls.

An Elo-style ability rating (T-103) runs beside BKT and never changes it: one
global theta (skill_id '*') and one per primary skill, updated only after an
independent first attempt with ``difficulty.elo_update``. Ratings start at
INITIAL_THETA = 0.25, the middle of the level-2 band on the [0, 1] difficulty
scale (b = level / 8), a cautious start for the 8-12 year olds the app targets.
"""
from datetime import datetime, timedelta, timezone

from . import difficulty as difficulty_module

INITIAL_THETA = 0.25
GLOBAL = '*'
_difficulty = None


def default_difficulty():
    """Shared Difficulty() built on first use, so old callers of record() keep working."""
    global _difficulty
    if _difficulty is None:
        _difficulty = difficulty_module.Difficulty()
    return _difficulty


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def update_probability(prior, correct, parameters):
    """Bayes observation followed by the learning transition (no forgetting)."""
    slip, guess, learn = (parameters[k] for k in ('slip', 'guess', 'learn'))
    numerator = prior * ((1 - slip) if correct else slip)
    likelihood = numerator + (1 - prior) * (guess if correct else (1 - guess))
    posterior = numerator / likelihood
    return posterior + (1 - posterior) * learn


def initialize(con):
    con.executescript('''
    CREATE TABLE IF NOT EXISTS student_skills (
      student TEXT NOT NULL, skill_id TEXT NOT NULL, mastery REAL NOT NULL,
      evidence INTEGER NOT NULL DEFAULT 0, successes INTEGER NOT NULL DEFAULT 0,
      review_stage INTEGER NOT NULL DEFAULT 0, next_review TEXT,
      last_practiced TEXT, PRIMARY KEY(student, skill_id));
    CREATE TABLE IF NOT EXISTS learning_events (
      id INTEGER PRIMARY KEY, attempt_id INTEGER UNIQUE NOT NULL,
      student TEXT NOT NULL, session_id TEXT NOT NULL, problem_id TEXT NOT NULL,
      language TEXT NOT NULL, kind TEXT NOT NULL, skill_id TEXT, correct INTEGER NOT NULL,
      first_attempt INTEGER NOT NULL, hints INTEGER NOT NULL, revealed INTEGER NOT NULL,
      eligible INTEGER NOT NULL, reason TEXT NOT NULL, before REAL, after REAL,
      seconds REAL NOT NULL, created TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS learning_student ON learning_events(student, created);
    CREATE TABLE IF NOT EXISTS curriculum_skills (id TEXT PRIMARY KEY, title TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS prerequisites (source TEXT, target TEXT, PRIMARY KEY(source,target));
    CREATE TABLE IF NOT EXISTS problem_skills (problem_id TEXT, skill_id TEXT, assessment INTEGER, PRIMARY KEY(problem_id,skill_id));
    CREATE TABLE IF NOT EXISTS thinking_events (
      id INTEGER PRIMARY KEY, student TEXT NOT NULL, session_id TEXT NOT NULL,
      problem_id TEXT NOT NULL, language TEXT NOT NULL, stage TEXT NOT NULL,
      skill_id TEXT, scope TEXT NOT NULL, choice INTEGER NOT NULL, correct INTEGER NOT NULL,
      first INTEGER NOT NULL, seconds REAL NOT NULL, created TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS thinking_student ON thinking_events(student, session_id);
    CREATE TABLE IF NOT EXISTS student_elo (
      student TEXT, skill_id TEXT, theta REAL NOT NULL,
      updates INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(student, skill_id));
    ''')
    columns = {r[1] for r in con.execute('PRAGMA table_info(sessions)')}
    for name, definition in [('started_at', 'TEXT'), ('return_to', 'TEXT'), ('last_answer', 'TEXT'), ('reflection', "TEXT NOT NULL DEFAULT ''"),
                             ('steps_done', 'INTEGER NOT NULL DEFAULT 0'), ('steps_wrong', 'INTEGER NOT NULL DEFAULT 0'),
                             ('misconception', 'TEXT')]:
        if name not in columns:
            con.execute(f'ALTER TABLE sessions ADD COLUMN {name} {definition}')
    event_columns = {r[1] for r in con.execute('PRAGMA table_info(learning_events)')}
    if 'reflection' not in event_columns:
        con.execute("ALTER TABLE learning_events ADD COLUMN reflection TEXT NOT NULL DEFAULT ''")
    if 'misconception' not in event_columns:
        con.execute('ALTER TABLE learning_events ADD COLUMN misconception TEXT')


def states(con, student, knowledge, now=None):
    now = now or utc_now()
    saved = {r['skill_id']: dict(r) for r in con.execute('SELECT * FROM student_skills WHERE student=?', (student,))}
    result = {}
    for sid, skill in knowledge.skills.items():
        row = saved.get(sid, {'mastery': knowledge.model['prior'], 'evidence': 0, 'successes': 0,
                              'next_review': None, 'last_practiced': None, 'review_stage': 0})
        demonstrated = (row['mastery'] >= knowledge.model['demonstrated_threshold']
                        and row['evidence'] >= knowledge.model['min_evidence']
                        and row['successes'] >= knowledge.model['min_successes'])
        due = bool(row['next_review'] and row['next_review'] <= now)
        state = 'not_assessed' if not row['evidence'] else 'demonstrated' if demonstrated else 'developing'
        result[sid] = dict(row, id=sid, name=skill['title'], description=skill['description'],
                          prerequisites=skill['prerequisites'], depth=skill['depth'], state=state,
                          due=due, display_state='due' if due else state,
                          probability=round(row['mastery'], 4) if row['evidence'] else None,
                          independent=row['successes'], attempts=row['evidence'])
    return result


def ratings(con, student):
    """{'global': theta, 'by_skill': {skill: theta}, 'updates': n} with the initial value when unrated."""
    rows = {r[0]: (r[1], r[2]) for r in con.execute('SELECT skill_id, theta, updates FROM student_elo WHERE student=?', (student,))}
    theta, updates = rows.pop(GLOBAL, (INITIAL_THETA, 0))
    return {'global': round(theta, 4), 'by_skill': {sid: round(v[0], 4) for sid, v in sorted(rows.items())}, 'updates': updates}


def theta(con, student, skill_id=GLOBAL):
    row = con.execute('SELECT theta FROM student_elo WHERE student=? AND skill_id=?', (student, skill_id)).fetchone()
    return row[0] if row else None


def update_elo(con, student, skill_id, b, correct):
    before = theta(con, student, skill_id)
    before = INITIAL_THETA if before is None else before
    after = difficulty_module.elo_update(before, b, correct)
    con.execute('''INSERT INTO student_elo(student,skill_id,theta,updates) VALUES(?,?,?,1)
      ON CONFLICT(student,skill_id) DO UPDATE SET theta=excluded.theta, updates=updates+1''', (student, skill_id, after))
    return before, after


def record(con, student, session, problem, annotation, correct, attempt_id, eligible, reason, knowledge, now=None, misconception=None,
           difficulty=None):
    """Store one answer. `misconception` (an error-signature op) is descriptive only: it never changes BKT.

    The Elo rating uses the attempt's own eligibility (independent first attempt),
    so the global theta also moves on unclassified or multi-skill problems that
    BKT cannot attribute to one skill.
    """
    now = now or utc_now()
    independent = eligible
    primary = annotation.get('assessment_skill')
    if not primary:
        eligible, reason = False, 'multi_skill_requires_diagnostic' if annotation.get('skills') else 'unclassified'
    old = states(con, student, knowledge, now).get(primary)
    before = old['mastery'] if old else None
    after = update_probability(before, correct, knowledge.model) if eligible else before
    # A due repeated item may refresh the review date, but never inflate mastery.
    repeat_review = bool(old and old['due'] and session['tries'] == 0 and not session['hints'] and not session['revealed'])
    if primary and (eligible or repeat_review):
        stage = old['review_stage']
        intervals = knowledge.model['review_days']
        stage = min(stage + 1, len(intervals)) if correct else 0
        days = intervals[max(0, stage - 1)] if correct else intervals[0]
        due = (datetime.fromisoformat(now) + timedelta(days=days)).isoformat(timespec='seconds')
        con.execute('''INSERT INTO student_skills(student,skill_id,mastery,evidence,successes,review_stage,next_review,last_practiced)
          VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(student,skill_id) DO UPDATE SET
          mastery=excluded.mastery,evidence=excluded.evidence,successes=excluded.successes,
          review_stage=excluded.review_stage,next_review=excluded.next_review,last_practiced=excluded.last_practiced''',
          (student, primary, after, old['evidence'] + int(eligible), old['successes'] + int(eligible and correct), stage, due, now))
        if repeat_review and not eligible:
            reason = 'spaced_repeat_review_only'
    started = datetime.fromisoformat(session['started_at'] or now)
    seconds = max(0, (datetime.fromisoformat(now) - started).total_seconds())
    con.execute('''INSERT INTO learning_events(attempt_id,student,session_id,problem_id,language,kind,skill_id,
      correct,first_attempt,hints,revealed,eligible,reason,before,after,seconds,created)
      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
      (attempt_id, student, session['id'], problem['id'], problem['language'], problem.get('kind', 'exercise'), primary,
       int(correct), int(session['tries'] == 0), session['hints'], session['revealed'], int(eligible), reason,
       before, after, seconds, now))
    con.execute('UPDATE learning_events SET reflection=?, misconception=? WHERE attempt_id=?',
                (session['reflection'] or '', misconception, attempt_id))
    current = theta(con, student)
    elo_before = elo_after = INITIAL_THETA if current is None else current
    if independent:
        b = (difficulty or default_difficulty()).b(problem['id'], problem.get('level'))
        elo_before, elo_after = update_elo(con, student, GLOBAL, b, correct)
        if primary:
            update_elo(con, student, primary, b, correct)
    return {'updated': eligible, 'skill_id': primary, 'reason': reason,
            'before': round(before, 4) if before is not None else None, 'after': round(after, 4) if after is not None else None,
            'elo_before': round(elo_before, 4), 'elo_after': round(elo_after, 4)}


STAGES = ('understand', 'plan', 'check')


def process(con, student, knowledge):
    """Thinking-step indicators. Descriptive only: steps never change mastery."""
    per_skill = {sid: {'asked': 0, 'correct_first': 0,
                       'by_stage': {stage: {'asked': 0, 'correct_first': 0} for stage in STAGES}}
                 for sid in knowledge.skills}
    for row in con.execute('''SELECT skill_id, stage, count(*), sum(correct) FROM thinking_events
                              WHERE student=? AND first=1 GROUP BY skill_id, stage''', (student,)):
        sid, stage, asked, right = row[0], row[1], row[2], row[3] or 0
        if sid not in per_skill or stage not in STAGES:
            continue
        per_skill[sid]['asked'] += asked
        per_skill[sid]['correct_first'] += right
        per_skill[sid]['by_stage'][stage] = {'asked': asked, 'correct_first': right}
    asked, right = con.execute('SELECT count(*), sum(correct) FROM thinking_events WHERE student=? AND first=1', (student,)).fetchone()
    all_right = con.execute('SELECT count(*) FROM sessions WHERE student=? AND steps_done>=? AND steps_wrong=0',
                            (student, len(STAGES))).fetchone()[0]

    def accuracy(condition):
        # Eligible first attempts only: the same events that BKT would use.
        total, correct = con.execute(f'''SELECT count(*), sum(e.correct) FROM learning_events e
            JOIN sessions s ON s.id=e.session_id WHERE e.student=? AND e.eligible=1 AND e.first_attempt=1
            AND s.steps_done>=? AND {condition}''', (student, len(STAGES))).fetchone()
        return round(correct / total, 4) if total else None
    summary = {'steps_first_try_rate': round((right or 0) / asked, 4) if asked else None,
               'problems_with_all_steps_right': all_right,
               'first_attempt_accuracy_when_steps_right': accuracy('s.steps_wrong=0'),
               'first_attempt_accuracy_when_step_missed': accuracy('s.steps_wrong>0')}
    return per_skill, summary


def report(con, student, knowledge, now=None):
    now = now or utc_now()
    clean_name = student.replace('\n', ' ').replace('|', ' ')
    lines = [f'# Learning notebook: {clean_name}', '', f'Generated: {now}', '',
             'Provisional BKT estimates; these are practice indicators, not validated mastery scores.',
             'Unassessed skills are unknown. Review dates do not reduce mastery.', '',
             '| Skill | State | Independent evidence | Estimated probability | Review due |',
             '| --- | --- | --- | --- | --- |']
    for row in states(con, student, knowledge, now).values():
        probability = f"{row['probability']:.0%}" if row['probability'] is not None else 'Not assessed'
        lines.append(f"| {row['name']} | {row['state']} | {row['evidence']} | {probability} | {row['next_review'] or '—'} |")
    lines.extend(['', '## Recent evidence', '', '| Problem | Language | Outcome | Attribution |', '| --- | --- | --- | --- |'])
    for row in con.execute('SELECT * FROM learning_events WHERE student=? ORDER BY id DESC LIMIT 20', (student,)):
        lines.append(f"| {row['problem_id']} | {row['language']} | {'Correct' if row['correct'] else 'Incorrect'} | {row['reason']} |")
    per_skill, summary = process(con, student, knowledge)
    lines.extend(['', '## Thinking process', '',
                  'Multiple-choice thinking steps answered before choosing a letter. Only the first choice per step counts here.', '',
                  '| Skill | Steps asked | Right first try | Understand | Plan | Check |', '| --- | --- | --- | --- | --- | --- |'])
    for sid, row in per_skill.items():
        if row['asked']:
            stages = [f"{s['correct_first']}/{s['asked']}" if s['asked'] else '—' for s in row['by_stage'].values()]
            lines.append(f"| {knowledge.skills[sid]['title']} | {row['asked']} | {row['correct_first']} | {' | '.join(stages)} |")
    if not any(row['asked'] for row in per_skill.values()):
        lines.append('| No thinking steps answered yet | 0 | 0 | — | — | — |')

    def percent(value):
        return 'no data' if value is None else f'{value:.0%}'
    lines.extend(['', f"First-attempt accuracy when every step was right first try: {percent(summary['first_attempt_accuracy_when_steps_right'])}; "
                      f"when a step was missed: {percent(summary['first_attempt_accuracy_when_step_missed'])}.",
                  'These are descriptive indicators, not validated learning gains, and they never change the skill estimates.'])
    slips = con.execute('''SELECT misconception, count(*) FROM learning_events WHERE student=? AND misconception IS NOT NULL
                           GROUP BY misconception ORDER BY count(*) DESC, misconception LIMIT 8''', (student,)).fetchall()
    if slips:
        lines.extend(['', '## Common slips', '',
                      'Wrong answers that match a naive operation on the numbers in the problem (likely slips, not diagnoses).', '',
                      '| Slip | Times |', '| --- | --- |'])
        lines.extend(f"| {row[0].replace('_', ' ')} | {row[1]} |" for row in slips)
    lines.extend(['', '## Student reasoning', '', 'Student-written notes; their mathematical correctness has not been assessed.', ''])
    for row in con.execute("SELECT problem_id,reflection FROM learning_events WHERE student=? AND reflection!='' ORDER BY id DESC LIMIT 10", (student,)):
        clean = row['reflection'].replace('\r', ' ').replace('\n', ' ')
        lines.extend([f"**{row['problem_id']}**", '', '> ' + clean, ''])
    return '\n'.join(lines) + '\n'
