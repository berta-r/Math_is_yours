"""Offline student practice app. Run: python student_app/server.py"""
import argparse
import json
import secrets
import sqlite3
import sys
import socket
import os
from contextlib import contextmanager
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
try:
    from .catalog import Catalog, default_inputs
except ImportError:
    from catalog import Catalog, default_inputs

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from copilot.knowledge import Knowledge, leaked
from copilot.misconceptions import Misconceptions
from copilot import student_model, scheduler
from copilot.config import CONFIG
from copilot.tutor import Tutor
from copilot.learning_graph import LearningGraph, build_path
from copilot.difficulty import Difficulty
from copilot.learning_map import LearningMap
ASSETS = Path(__file__).resolve().parent / "assets"

# Child-facing messages, by problem language. English is the fallback for any other language.
MESSAGES = {
    'eng': {
        'step_done': 'Yes. Now explore the answer choices.',
        'step_next': 'Yes. On to the next step.',
        'step_retry': 'Not yet. Read the explanation and try another option.',
        'correct_independent': 'Correct! You solved it on your own, first try.',
        'correct_assisted': 'Correct! This one counts as practice with help.',
        'wrong': 'Not quite. Try a hint or a short skill check to find the next step.',
        'multi_skill': 'This problem mixes several skills. A quick check will show what to practise next.',
        'reveal': 'The correct answer is {label}. From now on, this problem counts as practice with help.',
        'no_hints': 'There are no hints for this problem yet.',
        'no_solution': 'There is no explanation for this problem yet.',
        'reflect_saved': 'Your idea is saved. Now look at the choices and test it.',
        'language_fallback': 'This check is in English.',
        'repeat': "You have seen this one before, so it is extra practice.",
        'states': {'not_assessed': 'Not tried yet', 'developing': 'Getting there',
                   'demonstrated': 'Got it', 'due': 'Time to review'},
        'summary': {
            'diagnostic': "Let's see what you already know about {skill}.",
            'prerequisite': '{skill} will help you with harder problems. Practise it now.',
            'repair': 'Practise {skill} with a new problem.',
            'practice': 'Practise {skill} with a new problem.',
            'review': 'It is time to review {skill}.',
            'transfer': 'Try {skill} in a new kind of problem.',
            'path': 'Next step towards {goal}: {skill}.',
            'chosen': 'You chose to practise {skill}.',
            'stretch': 'A challenge in {skill}. Hints are ready if you need them.',
            'complete': 'You have tried every problem here. Pick any one for extra practice.',
        },
        'step_reason': {'not_assessed': 'Start with a quick check.', 'developing': 'Practise with a new problem.',
                        'demonstrated': 'Use it in a new kind of problem.', 'due': 'Time for a short review.'},
    },
    'cat': {
        'step_done': 'Molt bé. Ara mira les opcions de resposta.',
        'step_next': 'Molt bé. Passem al pas següent.',
        'step_retry': "Encara no. Llegeix l'explicació i prova una altra opció.",
        'correct_independent': "Correcte! L'has resolt pel teu compte al primer intent.",
        'correct_assisted': 'Correcte! Aquest compta com a pràctica amb ajuda.',
        'wrong': 'Gairebé. Demana una pista o fes una prova curta per trobar el pas següent.',
        'multi_skill': 'Aquest problema barreja diverses habilitats. Una prova curta et dirà què has de practicar.',
        'reveal': 'La resposta correcta és la {label}. A partir d’ara, aquest problema compta com a pràctica amb ajuda.',
        'no_hints': 'Encara no hi ha pistes per a aquest problema.',
        'no_solution': 'Encara no hi ha cap explicació per a aquest problema.',
        'reflect_saved': 'La teva idea està desada. Ara mira les opcions i posa-la a prova.',
        'language_fallback': 'Aquesta prova només està en anglès.',
        'repeat': 'Aquest ja l’has vist abans, així que és pràctica extra.',
        'states': {'not_assessed': 'Encara no l’has provat', 'developing': 'Hi estàs arribant',
                   'demonstrated': 'Ho tens!', 'due': 'Toca repassar'},
        'summary': {
            'diagnostic': 'Vegem què saps de {skill}.',
            'prerequisite': '{skill} t’ajudarà amb problemes més difícils. Practica-ho ara.',
            'repair': 'Practica {skill} amb un problema nou.',
            'practice': 'Practica {skill} amb un problema nou.',
            'review': 'És hora de repassar {skill}.',
            'transfer': 'Prova {skill} en un problema diferent.',
            'path': 'Pas següent cap a {goal}: {skill}.',
            'chosen': 'Has triat practicar {skill}.',
            'stretch': 'Un repte de {skill}. Si et cal, tens pistes.',
            'complete': 'Ja has provat tots els problemes. Tria el que vulguis per practicar més.',
        },
        'step_reason': {'not_assessed': 'Comença amb una prova curta.', 'developing': 'Practica amb un problema nou.',
                        'demonstrated': 'Fes-ho servir en un problema diferent.', 'due': 'Toca un repàs curt.'},
    },
}


def messages(language):
    """Message table for a problem language ('cat', 'eng', ...); English when unknown."""
    return MESSAGES.get(language if isinstance(language, str) else 'eng', MESSAGES['eng'])


def child_summary(result, language):
    """A plain sentence for the child; the technical `reason` stays for the method note."""
    table = messages(language)
    kind = result.get('kind') or 'practice'
    text = table['summary'].get(kind, table['summary']['practice']).format(skill=result.get('skill') or '', goal=result.get('goal_name') or result.get('skill') or '')
    if result.get('problem') and result.get('fresh') is False:
        text += ' ' + table['repeat']
    return text


FONTS = {'/fonts/archivo-latin.woff2': 'archivo-latin.woff2', '/fonts/archivo-latin-ext.woff2': 'archivo-latin-ext.woff2'}


@contextmanager
def connection(db):
    con = sqlite3.connect(db)
    try:
        with con:
            yield con
    finally:
        con.close()


def initialize(db):
    with connection(db) as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
          id TEXT PRIMARY KEY, student TEXT NOT NULL, problem TEXT NOT NULL,
          hints INTEGER NOT NULL DEFAULT 0, tries INTEGER NOT NULL DEFAULT 0,
          revealed INTEGER NOT NULL DEFAULT 0, solved INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS attempts (
          id INTEGER PRIMARY KEY, student TEXT NOT NULL, problem TEXT NOT NULL,
          answer TEXT NOT NULL, correct INTEGER NOT NULL, independent INTEGER NOT NULL,
          created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        """)
        student_model.initialize(con)


GENERATED = {'steps': ROOT / 'data/ml/thinking_steps_generated.json', 'solutions': ROOT / 'data/ml/solutions_generated.json',
             'annotations': ROOT / 'data/teaching_annotations.generated.json', 'explanations': ROOT / 'data/ml/slm_explanations.json'}


def make_handler(db, catalog=None, knowledge=None, include_diagnostics=True, local_tutor=False, signatures=None,
                 difficulty=None, map_path=None, explanations=GENERATED['explanations'], log=None):
    catalog = catalog or Catalog([ROOT / "data/sample_problems.jsonl"], ROOT / "data/images")
    knowledge = knowledge or Knowledge(annotations=[ROOT / 'data/teaching_annotations.json'])
    graph = LearningGraph(knowledge, artifact=ROOT / 'data/skill_graph.json')
    tutor = Tutor(enabled=local_tutor, port=int(CONFIG['LLM_PORT']))
    # Optional laptop artifact (T-108); missing file means no misconception feedback.
    misconceptions = Misconceptions(signatures or ROOT / 'data/ml/signatures.json', generated=explanations)
    # Optional laptop artifacts (T-102, T-106); missing files keep today's behaviour.
    difficulty = difficulty if difficulty is not None else Difficulty()
    difficulty_enabled = bool(difficulty.problems)
    problem_map = LearningMap(map_path)
    if include_diagnostics:
        for p in knowledge.diagnostics:
            catalog.problems[p['id'] + '|' + p['language']] = p
    problems = catalog.problems
    # Problem-specific thinking steps must not contain the correct option's value.
    for key, p in problems.items():
        steps, scope = knowledge.thinking_steps(p)
        label = p.get('label')
        if scope == 'problem' and label in list('ABCDE') and leaked(steps, p.get('options', {}).get(label)):
            raise ValueError(f'Thinking steps for {key} contain the correct option value')
    # Large-model content (D-013) is re-verified against each loaded problem; failures are dropped, not served.
    report = knowledge.generated_report(problems.values())
    report['explanations'] = misconceptions.generated_report(problems.values())
    if log and any(v['loaded'] or v['dropped'] for v in report.values()):
        log('Generated content: ' + ', '.join(f"{name} {v['loaded']} served/{v['dropped']} dropped"
                                               for name, v in report.items()) + ' (dropped = failed re-verification)')
    with connection(db) as con:
        for sid, skill in knowledge.skills.items():
            con.execute('INSERT OR REPLACE INTO curriculum_skills(id,title) VALUES(?,?)', (sid, skill['title']))
        con.execute('DELETE FROM prerequisites')
        con.execute('DELETE FROM problem_skills')
        for edge in knowledge.public_graph():
            con.execute('INSERT INTO prerequisites(source,target) VALUES(?,?)', (edge['source'], edge['target']))
        for p in problems.values():
            annotation = knowledge.annotation(p)
            for sid in annotation['skills']:
                con.execute('INSERT OR REPLACE INTO problem_skills VALUES(?,?,?)', (p['id'], sid, int(sid == annotation.get('assessment_skill'))))

    def content(key):
        p = problems[key]
        annotation = knowledge.annotation(p)
        names = [knowledge.skills[sid]['title'] for sid in annotation['skills']]
        hints, _ = knowledge.hints(p)
        return (' + '.join(names) or 'Unclassified', hints, knowledge.solution(p)[0])

    def coverage():
        exercises = [p for p in problems.values() if p.get('kind') != 'diagnostic']
        sources = [knowledge.tag_source(p) for p in exercises]
        return {'tagged': sum(bool(s) for s in sources), 'tagged_human': sources.count('human'),
                'tagged_generated': sources.count('generated'), 'exercises': len(exercises)}

    by_id = {}
    for key, p in problems.items():
        by_id.setdefault(p['id'], {}).setdefault(p['language'], key)

    def solved_and_exposed(con, student):
        """Canonical ids with a correct attempt, and ids seen (tried, hinted or revealed) by this student."""
        solved = {r[0].split('|')[0] for r in con.execute('SELECT problem FROM attempts WHERE student=? AND correct=1', (student,))}
        exposed = {r[0].split('|')[0] for r in con.execute(
            'SELECT problem FROM sessions WHERE student=? AND (tries>0 OR hints>0 OR revealed>0)', (student,))}
        return solved, exposed

    def map_view(con, student, body):
        if not problem_map.enabled:
            return {'enabled': False, 'nodes': [], 'clusters': [], 'edges': [], 'student_b_mean': None}
        solved, exposed = solved_and_exposed(con, student)
        nodes = [{'id': n['id'], 'level': n['level'], 'x': n['x'], 'y': n['y'], 'cluster': n['cluster'], 'b': round(n['b'], 4),
                  'solved': n['id'] in solved, 'exposed': n['id'] in exposed or n['id'] in solved, 'languages': n['languages']}
                 for n in problem_map.nodes]
        solved_b = [n['b'] for n in nodes if n['solved']]
        # Edges are [source index, target index, weight] into nodes; omit with {"edges": false}.
        edges = [[a, b, round(w, 3)] for a, b, w in problem_map.edges] if body.get('edges', True) is not False else []
        return {'enabled': True, 'nodes': nodes, 'clusters': problem_map.clusters(), 'edges': edges,
                'student_b_mean': round(sum(solved_b) / len(solved_b), 4) if solved_b else None}

    # Map decoration (T-117): skill tag, cluster category and difficulty tertiles per node.
    map_skill = {}
    for n in problem_map.nodes:
        tags = knowledge.annotation({'id': n['id']})
        map_skill[n['id']] = tags.get('assessment_skill') or next(iter(tags.get('skills') or []), None)
    map_category = {c['id']: ', '.join((c.get('keywords') or [])[:3]) for c in problem_map.clusters()}
    map_b = sorted(n['b'] for n in problem_map.nodes)
    map_tertiles = (map_b[len(map_b) // 3], map_b[(2 * len(map_b)) // 3]) if map_b else (None, None)

    def skill_title(sid):
        return knowledge.skills[sid]['title'] if sid in knowledge.skills else None

    def difficulty_label(b):
        if b is None or map_tertiles[0] is None:
            return None
        return 'easy' if b <= map_tertiles[0] else 'medium' if b <= map_tertiles[1] else 'hard'

    def map_step(pid, language, solved=()):
        node = problem_map.node(pid) or {}
        keys = by_id.get(pid, {})
        key = keys.get(language) or keys.get('eng') or (next(iter(sorted(keys.values()))) if keys else None)
        text = problems[key].get('text') if key else None
        sid = map_skill.get(pid)
        return {'id': pid, 'level': node.get('level'), 'b': node.get('b'), 'cluster': node.get('cluster'),
                'key': key, 'text_preview': text[:90] if isinstance(text, str) else None,
                'skill': sid, 'skill_name': skill_title(sid), 'category': map_category.get(node.get('cluster')),
                'difficulty_label': difficulty_label(node.get('b')), 'solved': pid in solved}

    def goal_for_skill(sid, solved):
        """Goal problem for a skill: unsolved tagged node closest to the student's mean b + 0.5, else the easiest tagged."""
        tagged = [n for n in problem_map.nodes if sid in (knowledge.annotation({'id': n['id']}).get('skills') or [])]
        if not tagged:
            return None
        solved_b = [n['b'] for n in problem_map.nodes if n['id'] in solved]
        target = (sum(solved_b) / len(solved_b) if solved_b else 0.0) + 0.5
        pool = [n for n in tagged if n['id'] not in solved] or tagged
        return min(pool, key=lambda n: (abs(n['b'] - target), n['id']))['id']

    def map_path(con, student, body):
        goal, goal_skill, language = body.get('goal'), body.get('goal_skill'), body.get('language') or 'eng'
        if goal_skill is not None and goal_skill not in knowledge.skills:
            raise ValueError('Unknown goal skill')
        if goal_skill is None and (not isinstance(goal, str) or not goal):
            raise ValueError('Choose a goal problem on the map')
        if not problem_map.enabled:
            return {'enabled': False, 'goal': goal, 'goal_skill': goal_skill, 'goal_skill_name': skill_title(goal_skill),
                    'goal_problem': None, 'steps': [], 'frontier': [], 'reachable': False, 'reason': 'The problem map is not installed.'}
        solved, _ = solved_and_exposed(con, student)
        solved = sorted(solved)
        frontier = [dict(map_step(f['id'], language, solved), gap=f['gap'], via=f['via']) for f in problem_map.frontier(solved)]
        if goal_skill is not None:
            goal = goal_for_skill(goal_skill, solved)
            if goal is None:
                return {'enabled': True, 'goal': None, 'goal_skill': goal_skill, 'goal_skill_name': skill_title(goal_skill),
                        'goal_problem': None, 'steps': [], 'cost': None, 'remaining': 0, 'reachable': False,
                        'frontier': frontier, 'reason': 'No problem on the map is tagged with this skill yet.'}
        route = problem_map.path(solved, goal)  # unknown goal -> ValueError -> 400
        goal_problem = map_step(goal, language, solved)
        return dict(route, enabled=True, steps=[map_step(pid, language, solved) for pid in route['steps']], frontier=frontier,
                    goal_problem=goal_problem, goal_skill=goal_skill or goal_problem['skill'],
                    goal_skill_name=skill_title(goal_skill or goal_problem['skill']))

    def rating_for(con, student, skill_id=None):
        """Theta for the selected skill, else the global rating, else the initial value."""
        value = student_model.theta(con, student, skill_id) if skill_id else None
        if value is None:
            value = student_model.theta(con, student)
        return student_model.INITIAL_THETA if value is None else value

    def ready(session, key):
        """Thinking gate: all thinking steps done, or a written thought when no steps exist."""
        steps, _ = knowledge.thinking_steps(problems[key])
        return bool(session['steps_done'] >= len(steps)) if steps else bool(session['reflection'])

    def can_reveal(session, key):
        return bool(session['solved'] or (ready(session, key) and session['tries'] >= 2
                    and (session['hints'] > 0 or not content(key)[1])))

    def steps_summary(con, session, key):
        steps, _ = knowledge.thinking_steps(problems[key])
        first = {r['stage']: r['correct'] for r in con.execute(
            'SELECT stage, correct FROM thinking_events WHERE session_id=? AND first=1', (session['id'],))}
        return '; '.join(f"{s['stage']} step {'not reached' if s['stage'] not in first else 'ok' if first[s['stage']] else 'missed'}"
                         for s in steps)

    def learning_route(con, student, body):
        state = student_model.states(con, student, knowledge)
        goal = body.get('goal')
        if not goal and body.get('focus'):
            session = con.execute('SELECT * FROM sessions WHERE id=? AND student=?', (body['focus'], student)).fetchone()
            if session:
                problem = problems.get(session['return_to'] or session['problem'])
                tags = knowledge.annotation(problem)['skills'] if problem else []
                if tags:
                    goal = min(tags, key=lambda sid: (state[sid]['evidence'] > 0, state[sid]['mastery'], sid))
        route = build_path(state, knowledge, goal=goal, related_edges=graph.related_edges)
        reasons = messages(body.get('language'))['step_reason']
        for step in route['steps']:
            step['child_reason'] = reasons['due'] if step.get('due') else reasons.get(step['state'], step['reason'])
        return route

    def thinking_step(con, student, session, key, body):
        """Check one multiple-choice process question. Pure Python: no model call, no mastery update."""
        steps, scope = knowledge.thinking_steps(problems[key])
        if not steps:
            raise ValueError('This problem has no thinking steps. Write a first thought instead.')
        index, choice = body.get('index'), body.get('choice')
        if session['steps_done'] >= len(steps):
            raise ValueError('All thinking steps are already done. Explore the answer choices.')
        if type(index) is not int or index != session['steps_done']:
            raise ValueError('Answer the current thinking step first.')
        if type(choice) is not int or not 0 <= choice <= 2:
            raise ValueError('Choose one of the three options.')
        step = steps[index]
        correct = choice == step['answer']
        first = not con.execute('SELECT 1 FROM thinking_events WHERE session_id=? AND stage=?', (session['id'], step['stage'])).fetchone()
        now = student_model.utc_now()
        previous = con.execute('SELECT max(created) FROM thinking_events WHERE session_id=?', (session['id'],)).fetchone()[0]
        started = datetime.fromisoformat(previous or session['started_at'] or now)
        seconds = max(0.0, (datetime.fromisoformat(now) - started).total_seconds())
        con.execute('''INSERT INTO thinking_events(student,session_id,problem_id,language,stage,skill_id,scope,choice,correct,first,seconds,created)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (student, session['id'], problems[key]['id'], problems[key]['language'], step['stage'],
                     knowledge.steps_skill(problems[key]), scope, choice, int(correct), int(first), seconds, now))
        done = session['steps_done'] + int(correct)
        con.execute('UPDATE sessions SET steps_done=?, steps_wrong=steps_wrong+? WHERE id=?', (done, int(not correct), session['id']))
        completed = done >= len(steps)
        table = messages(problems[key]['language'])
        message = table['step_done' if completed else 'step_next'] if correct else table['step_retry']
        return {'correct': correct, 'why': step['why'], 'stage': step['stage'], 'next_index': done,
                'completed': completed, 'message': message}

    class Handler(BaseHTTPRequestHandler):
        teaching_tutor = tutor

        def send_json(self, value, status=200):
            raw = json.dumps(value, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == '/api/health':
                return self.send_json({'app': 'math-is-yours', 'version': 'connected-graph-v2',
                                       'status': 'ready', 'tutor': 'local' if local_tutor else 'stored',
                                       'model': tutor.health()})
            if path == "/api/image":
                query = parse_qs(urlsplit(self.path).query)
                key = query.get("key", [""])[0]
                option = query.get('option', [None])[0]
                image = catalog.image(key, option) if key in problems else None
                if image is None:
                    return self.send_json({"error": "Image not found. Prepare data with --save-images."}, 404)
                raw = image.read_bytes()
                # The preparation script preserves image bytes under .png names.
                mime = "image/jpeg" if raw.startswith(b"\xff\xd8\xff") else "image/webp" if raw[:4] == b"RIFF" else "image/png"
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                return
            if path in FONTS:
                raw = (ASSETS / 'fonts' / FONTS[path]).read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', 'font/woff2')  # binary: no charset
                self.send_header('Cache-Control', 'max-age=86400')
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                return
            files = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"), "/graph.js": ("graph.js", "text/javascript"), "/style.css": ("style.css", "text/css"),
                     '/map': ('map.html', 'text/html'), '/map.js': ('map.js', 'text/javascript')}
            if path not in files:
                return self.send_json({"error": "Not found"}, 404)
            filename, mime = files[path]
            raw = (ASSETS / filename).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mime + "; charset=utf-8")
            self.send_header('Cache-Control', 'no-store')
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self):
            # Only the same-origin browser app may mutate local records.
            origin = self.headers.get("Origin")
            if origin and origin != "http://" + self.headers.get("Host", ""):
                return self.send_json({"error": "Origin rejected"}, 403)
            try:
                size = int(self.headers.get("Content-Length", 0))
                if not 0 < size <= 16384:
                    raise ValueError("Invalid request size")
                body = json.loads(self.rfile.read(size))
                if not isinstance(body, dict):
                    raise ValueError("Expected an object")
                student = body.get("student", "")
                if not isinstance(student, str) or not 1 <= len(student.strip()) <= 40:
                    raise ValueError("Enter a student nickname (1–40 characters)")
                student = student.strip()
                with connection(db) as con:
                    con.row_factory = sqlite3.Row
                    # Serialize exposure checks with writes: double submissions and
                    # simultaneous translated variants cannot earn duplicate evidence.
                    con.execute('BEGIN IMMEDIATE')
                    result = self.action(con, urlsplit(self.path).path, student, body)
                self.send_json(result)
            except (ValueError, KeyError, TypeError) as error:
                self.send_json({"error": str(error)}, 400)

        def action(self, con, path, student, body):
            if path == "/api/profile":
                skills = list(student_model.states(con, student, knowledge).values())
                history = [dict(r) for r in con.execute('SELECT problem_id,language,kind,skill_id,correct,eligible,reason,created FROM learning_events WHERE student=? ORDER BY id DESC LIMIT 12', (student,))]
                process, process_summary = student_model.process(con, student, knowledge)
                return {'skills': skills, 'edges': knowledge.public_graph(), 'history': history,
                        'process': process, 'process_summary': process_summary,
                        'related_edges': graph.related_edges, 'graph_method': graph.method,
                        'learning_path': learning_route(con, student, body),
                        'rating': student_model.ratings(con, student), 'difficulty_enabled': difficulty_enabled,
                        'attempts': con.execute('SELECT count(*) FROM attempts WHERE student=?', (student,)).fetchone()[0],
                        'parameters': knowledge.model, 'tutor': 'local selection' if local_tutor else 'stored guidance',
                        'coverage': coverage(), 'state_labels': messages(body.get('language'))['states']}
            if path == '/api/recommendation':
                goal = body.get('goal')
                learning_path = learning_route(con, student, body)
                selected_skill = body.get('skill') or learning_path.get('next_skill')
                step = next((s for s in learning_path['steps'] if s['id'] == selected_skill), None)
                result = scheduler.recommend(con, student, catalog, knowledge, focus=body.get('focus'),
                                           language=body.get('language') or 'eng', skill_id=selected_skill,
                                           preferred_kind='diagnostic' if step and step['state'] == 'not_assessed' else None,
                                           prefer_assessment=not body.get('skill'),
                                           difficulty=difficulty if difficulty_enabled else None,
                                           theta=rating_for(con, student, selected_skill) if difficulty_enabled else None)
                if not body.get('skill') and result.get('problem'):
                    step = next(s for s in learning_path['steps'] if s['id'] == selected_skill)
                    kind = 'path' if goal else 'review' if step['due'] else 'prerequisite' if step['role'] == 'support' else 'diagnostic' if step['state'] == 'not_assessed' else 'transfer' if step['state'] == 'demonstrated' else 'repair'
                    result.update(kind=kind, reason=learning_path['reason'] + ' ' + step['reason'])
                    if result.get('difficulty_reason'):
                        result['reason'] += ' ' + result['difficulty_reason']
                    if body.get('focus'):
                        previous = con.execute('SELECT problem,return_to FROM sessions WHERE id=? AND student=?', (body['focus'], student)).fetchone()
                        if previous:
                            result['return_to'] = previous['return_to'] or previous['problem']
                    if not result['fresh']:
                        result['reason'] += ' This repeats an exposed item; it will not count as new independent evidence.'
                language = body.get('language') or 'eng'
                result['goal_name'] = learning_path.get('goal_name') if goal else None
                result['summary'] = child_summary(result, language)
                if result.get('language_fallback'):
                    result['language_note'] = messages(language)['language_fallback']
                result['learning_path'] = learning_path
                return result
            if path == '/api/map':
                return map_view(con, student, body)
            if path == '/api/path':
                return map_path(con, student, body)
            if path == '/api/report':
                return {'markdown': student_model.report(con, student, knowledge)}
            if path == '/api/hint-job':
                return tutor.status(student, body.get('job'))
            if path == "/api/start":
                pid = catalog.resolve(body.get("problem"))
                return_to = body.get('return_to')
                if return_to:
                    return_to = catalog.resolve(return_to)
                sid = secrets.token_urlsafe(24)
                con.execute("INSERT INTO sessions(id,student,problem,started_at,return_to) VALUES(?,?,?,?,?)", (sid, student, pid, student_model.utc_now(), return_to))
                steps, steps_scope = knowledge.thinking_steps(problems[pid])
                steps_skill = knowledge.steps_skill(problems[pid])
                return {"session": sid, "problem": catalog.public(pid), "skill": content(pid)[0],
                        'skills': knowledge.annotation(problems[pid])['skills'],
                        'assessment_skill': knowledge.annotation(problems[pid]).get('assessment_skill'),
                        'kind': problems[pid].get('kind', 'exercise'),
                        # Answers and explanations stay on the server until a choice is made.
                        'thinking_steps': [{'stage': s['stage'], 'question': s['question'], 'options': s['options']} for s in steps],
                        'steps_scope': steps_scope, 'steps_language': steps[0]['language'] if steps else None,
                        'steps_skill': knowledge.skills[steps_skill]['title'] if steps and steps_skill else None,
                        'reflection_required': not steps, 'can_reveal': False,
                        'reflection_prompt': 'What do you notice? Describe a first step, a useful relationship, or what you are unsure about before choosing an answer.',
                        "has_hints": bool(content(pid)[1]), "has_solution": bool(content(pid)[2]),
                        # Where each kind of help comes from: problem (human), generated (large model, verified), skill, template, none.
                        'content_sources': {'steps': steps_scope, 'hints': knowledge.hints(problems[pid])[1],
                                            'solution': knowledge.solution(problems[pid])[1],
                                            'explanations': misconceptions.source(problems[pid])},
                        'tags_source': knowledge.tag_source(problems[pid]),
                        'provenance': knowledge.annotation(problems[pid]).get('provenance')}
            if path == "/api/problems":
                return {'version': 'connected-graph-v2', "sources": catalog.sources, 'coverage': coverage(),
                        "problems": [{"key": key, "id": p["id"], "skill": content(key)[0],
                         'skills': knowledge.annotation(p)['skills'], 'tags_source': knowledge.tag_source(p), 'kind': p.get('kind', 'exercise'),
                         "language": p["language"], "format": catalog.public(key)["format"],
                         # A short, child-readable label for the problem picker (T-101).
                         'preview': ' '.join((p.get('text') or '').split())[:60]} for key, p in problems.items()]}
            if path not in ("/api/answer", "/api/hint", "/api/solution", "/api/reveal", '/api/reflect', '/api/step'):
                raise ValueError("Unknown action")
            session = con.execute("SELECT * FROM sessions WHERE id=? AND student=?", (body.get("session"), student)).fetchone()
            if session is None:
                raise ValueError("Open a problem first")
            pid = session["problem"]
            if pid not in problems:
                raise ValueError("This problem is no longer loaded. Open another problem.")
            table = messages(problems[pid]['language'])
            if path == '/api/reflect':
                reflection = body.get('reflection')
                if not isinstance(reflection, str) or not 5 <= len(reflection.strip()) <= 1200:
                    raise ValueError('Write a short thought or question (5–1200 characters) before choosing an answer.')
                con.execute('UPDATE sessions SET reflection=? WHERE id=?', (reflection.strip(), session['id']))
                return {'reflection_saved': True, 'message': table['reflect_saved']}
            if path == '/api/step':
                return thinking_step(con, student, session, pid, body)
            if path in ('/api/reveal', '/api/solution') and not can_reveal(session, pid):
                raise ValueError('First work through your thinking, make two attempts, and try a hint when available. Then you can review the answer.')
            if path == "/api/reveal":
                label = problems[pid].get("label")
                if label not in list("ABCDE"):
                    raise ValueError("No official answer key is available for this problem.")
                con.execute("UPDATE sessions SET revealed=1 WHERE id=?", (session["id"],))
                return {"answer": label, "message": table['reveal'].format(label=label)}
            if path == "/api/hint":
                # After a wrong answer with a generated Socratic question, that question is the first hint.
                slip = misconceptions.explain(problems[pid], session['last_answer']) if session['last_answer'] and not session['solved'] else None
                if slip and slip.get('question') and session['hints'] == 0:
                    con.execute('UPDATE sessions SET hints=hints+1, question_hints=question_hints+1 WHERE id=?', (session['id'],))
                    return {'message': slip['question'], 'source': 'generated', 'scope': 'question', 'rung': 0,
                            'can_reveal': can_reveal(dict(session, hints=session['hints'] + 1), pid)}
                hints, scope = knowledge.hints(problems[pid])
                if not hints:
                    return {"message": table['no_hints'], 'can_reveal': can_reveal(session, pid)}
                # A missed plan step or a recognised slip means the student needs the method,
                # so skip the broad first prompt.
                missed_plan = session['steps_wrong'] > 0 and con.execute(
                    "SELECT 1 FROM thinking_events WHERE session_id=? AND stage='plan' AND first=1 AND correct=0", (session['id'],)).fetchone()
                ladder = session['hints'] - session['question_hints']  # the question is not a ladder rung
                rung = min(ladder + (1 if missed_plan or session['misconception'] else 0), len(hints) - 1)
                con.execute("UPDATE sessions SET hints=hints+1 WHERE id=?", (session["id"],))
                context = session['reflection'] or steps_summary(con, session, pid)
                if session['misconception']:
                    context += f"; misconception: {session['misconception']}"
                result = tutor.request(student, problems[pid], content(pid)[0], session['last_answer'], hints, rung, scope, reflection=context)
                updated = dict(session, hints=session['hints'] + 1)
                return dict(result, can_reveal=can_reveal(updated, pid))
            if path == "/api/solution":
                text, scope = knowledge.solution(problems[pid])
                if not text:
                    return {"message": table['no_solution']}
                con.execute("UPDATE sessions SET revealed=1 WHERE id=?", (session["id"],))
                return {"message": text, 'scope': scope}
            answer = body.get("answer")
            if not ready(session, pid):
                if knowledge.thinking_steps(problems[pid])[0]:
                    raise ValueError('Work through the thinking steps before selecting an answer.')
                raise ValueError('Share a first thought before selecting an answer.')
            if answer not in list("ABCDE"):
                raise ValueError("Choose an answer")
            if session["solved"]:
                raise ValueError("Already solved. Open another problem.")
            if problems[pid].get("label") not in list("ABCDE"):
                raise ValueError("No answer key is available; this problem is view-only.")
            correct = answer == problems[pid]["label"]
            canonical = problems[pid]['id']
            prefix = canonical + '|'
            # Include old translations even if they are no longer in this catalog.
            seen = con.execute('SELECT 1 FROM sessions WHERE student=? AND (problem=? OR substr(problem,1,?)=?) AND id<>? AND (tries>0 OR hints>0 OR revealed=1) LIMIT 1',
                               (student, canonical, len(prefix), prefix, session['id'])).fetchone()
            eligible = not seen and not (session["tries"] or session["hints"] or session["revealed"])
            independent = correct and eligible
            attempt_id = con.execute("INSERT INTO attempts(student,problem,answer,correct,independent) VALUES(?,?,?,?,?)", (student, pid, answer, int(correct), int(independent))).lastrowid
            reason = 'independent_first_attempt' if eligible else 'assisted' if session['hints'] or session['revealed'] else 'repeat_or_translation'
            slip = None if correct else misconceptions.explain(problems[pid], answer)
            evidence = student_model.record(con, student, session, problems[pid], knowledge.annotation(problems[pid]), correct,
                                            attempt_id, eligible, reason, knowledge, misconception=slip and slip['op'],
                                            difficulty=difficulty)
            con.execute("UPDATE sessions SET tries=tries+1, solved=?, last_answer=?, misconception=? WHERE id=?",
                        (int(correct), answer, slip['op'] if slip else session['misconception'], session["id"]))
            message = table['correct_independent' if independent else 'correct_assisted'] if correct else table['wrong']
            if evidence['reason'] == 'multi_skill_requires_diagnostic':
                message += ' ' + table['multi_skill']
            result = {"correct": correct, "message": message, 'evidence': evidence,
                      'can_reveal': can_reveal(dict(session, tries=session['tries'] + 1, solved=int(correct)), pid)}
            if slip:
                result['message'] += ' ' + slip['message']
                result['misconception'] = {'op': slip['op'], 'answer_op': slip['answer_op']}
                if slip['source'] == 'generated':
                    result['misconception'].update(question=slip['question'], source='generated')
            return result
    return Handler


class StudentServer(ThreadingHTTPServer):
    # Windows address reuse can silently leave an old server answering requests.
    allow_reuse_address = os.name != 'nt'

    def server_bind(self):
        if os.name == 'nt' and hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

    def server_close(self):
        super().server_close()
        self.RequestHandlerClass.teaching_tutor.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=7011)
    parser.add_argument("--db", type=Path, default=Path(__file__).parent / "progress.db")
    parser.add_argument("--input", type=Path, nargs="+", help="Prepared JSONL files (default: data/train.jsonl, otherwise samples)")
    parser.add_argument("--images", type=Path, default=ROOT / "data/images")
    parser.add_argument('--annotations', type=Path, default=ROOT / 'data/teaching_annotations.json')
    # Optional large-model content (D-013); absent files keep today's behaviour.
    parser.add_argument('--generated-steps', type=Path, default=GENERATED['steps'])
    parser.add_argument('--generated-solutions', type=Path, default=GENERATED['solutions'])
    parser.add_argument('--generated-annotations', type=Path, default=GENERATED['annotations'])
    parser.add_argument('--generated-explanations', type=Path, default=GENERATED['explanations'])
    parser.add_argument('--local-tutor', action='store_true', help='Let the local SLM select from authored hints; stored fallback always available')
    args = parser.parse_args()
    try:
        catalog = Catalog(args.input or default_inputs(ROOT), args.images)
        knowledge = Knowledge(annotations=[args.annotations], generated_steps=args.generated_steps,
                              generated_solutions=args.generated_solutions, generated_annotations=args.generated_annotations)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    initialize(args.db)
    try:
        handler = make_handler(args.db, catalog, knowledge=knowledge, local_tutor=args.local_tutor,
                               explanations=args.generated_explanations, log=lambda line: print(line, flush=True))
    except (OSError, ValueError) as error:
        parser.error(str(error))
    try:
        server = StudentServer(("127.0.0.1", args.port), handler)
    except OSError as error:
        handler.teaching_tutor.close()
        parser.error(f'Cannot listen on port {args.port}: {error}. Stop the old server with Ctrl+C first.')
    print(f"Loaded {len(catalog.problems)} problems from {', '.join(catalog.sources)}", flush=True)
    print(f"Open http://127.0.0.1:{args.port} — Ctrl+C to stop", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
