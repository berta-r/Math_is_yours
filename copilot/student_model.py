"""Provisional BKT and separate review dates. No model fitting or network calls."""
from datetime import datetime, timedelta, timezone


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
    ''')
    columns = {r[1] for r in con.execute('PRAGMA table_info(sessions)')}
    for name, definition in [('started_at', 'TEXT'), ('return_to', 'TEXT'), ('last_answer', 'TEXT'), ('reflection', "TEXT NOT NULL DEFAULT ''")]:
        if name not in columns:
            con.execute(f'ALTER TABLE sessions ADD COLUMN {name} {definition}')
    event_columns = {r[1] for r in con.execute('PRAGMA table_info(learning_events)')}
    if 'reflection' not in event_columns:
        con.execute("ALTER TABLE learning_events ADD COLUMN reflection TEXT NOT NULL DEFAULT ''")


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


def record(con, student, session, problem, annotation, correct, attempt_id, eligible, reason, knowledge, now=None):
    now = now or utc_now()
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
    con.execute('UPDATE learning_events SET reflection=? WHERE attempt_id=?', (session['reflection'] or '', attempt_id))
    return {'updated': eligible, 'skill_id': primary, 'reason': reason,
            'before': round(before, 4) if before is not None else None, 'after': round(after, 4) if after is not None else None}


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
    lines.extend(['', '## Student reasoning', '', 'Student-written notes; their mathematical correctness has not been assessed.', ''])
    for row in con.execute("SELECT problem_id,reflection FROM learning_events WHERE student=? AND reflection!='' ORDER BY id DESC LIMIT 10", (student,)):
        clean = row['reflection'].replace('\r', ' ').replace('\n', ' ')
        lines.extend([f"**{row['problem_id']}**", '', '> ' + clean, ''])
    return '\n'.join(lines) + '\n'
