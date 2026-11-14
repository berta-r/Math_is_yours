"""Offline student practice app. Run: python student_app/server.py"""
import argparse
import json
import secrets
import sqlite3
import sys
import socket
import os
from contextlib import contextmanager
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
from copilot.knowledge import Knowledge
from copilot import student_model, scheduler
from copilot.config import CONFIG
from copilot.tutor import Tutor
from copilot.learning_graph import LearningGraph, build_path
ASSETS = Path(__file__).resolve().parent / "assets"


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


def make_handler(db, catalog=None, knowledge=None, include_diagnostics=True, local_tutor=False):
    catalog = catalog or Catalog([ROOT / "data/sample_problems.jsonl"], ROOT / "data/images")
    knowledge = knowledge or Knowledge(annotations=[ROOT / 'data/teaching_annotations.json'])
    graph = LearningGraph(knowledge, artifact=ROOT / 'data/skill_graph.json')
    tutor = Tutor(enabled=local_tutor, port=int(CONFIG['LLM_PORT']))
    if include_diagnostics:
        for p in knowledge.diagnostics:
            catalog.problems[p['id'] + '|' + p['language']] = p
    problems = catalog.problems
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
        return (' + '.join(names) or 'Unclassified', hints, annotation.get('solution') if annotation.get('language', 'eng') == p['language'] else None)

    def can_reveal(session, key):
        return bool(session['solved'] or (session['reflection'] and session['tries'] >= 2
                    and (session['hints'] > 0 or not content(key)[1])))

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
        return build_path(state, knowledge, goal=goal, related_edges=graph.related_edges)

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
                return self.send_json({'app': 'kangaroo-student', 'version': 'connected-graph-v2',
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
            files = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"), "/graph.js": ("graph.js", "text/javascript"), "/style.css": ("style.css", "text/css")}
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
                return {'skills': skills, 'edges': knowledge.public_graph(), 'history': history,
                        'related_edges': graph.related_edges, 'graph_method': graph.method,
                        'learning_path': learning_route(con, student, body),
                        'attempts': con.execute('SELECT count(*) FROM attempts WHERE student=?', (student,)).fetchone()[0],
                        'parameters': knowledge.model, 'tutor': 'local selection' if local_tutor else 'stored guidance',
                        'coverage': {'tagged': sum(bool(knowledge.annotation(p)['skills']) for p in problems.values() if p.get('kind') != 'diagnostic'),
                                     'exercises': sum(p.get('kind') != 'diagnostic' for p in problems.values())}}
            if path == '/api/recommendation':
                goal = body.get('goal')
                learning_path = learning_route(con, student, body)
                selected_skill = body.get('skill') or learning_path.get('next_skill')
                step = next((s for s in learning_path['steps'] if s['id'] == selected_skill), None)
                result = scheduler.recommend(con, student, catalog, knowledge, focus=body.get('focus'),
                                           language=body.get('language') or 'eng', skill_id=selected_skill,
                                           preferred_kind='diagnostic' if step and step['state'] == 'not_assessed' else None,
                                           prefer_assessment=not body.get('skill'))
                if not body.get('skill') and result.get('problem'):
                    step = next(s for s in learning_path['steps'] if s['id'] == selected_skill)
                    kind = 'path' if goal else 'review' if step['due'] else 'prerequisite' if step['role'] == 'support' else 'diagnostic' if step['state'] == 'not_assessed' else 'transfer' if step['state'] == 'demonstrated' else 'repair'
                    result.update(kind=kind, reason=learning_path['reason'] + ' ' + step['reason'])
                    if body.get('focus'):
                        previous = con.execute('SELECT problem,return_to FROM sessions WHERE id=? AND student=?', (body['focus'], student)).fetchone()
                        if previous:
                            result['return_to'] = previous['return_to'] or previous['problem']
                    if not result['fresh']:
                        result['reason'] += ' This repeats an exposed item; it will not count as new independent evidence.'
                result['learning_path'] = learning_path
                return result
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
                return {"session": sid, "problem": catalog.public(pid), "skill": content(pid)[0],
                        'skills': knowledge.annotation(problems[pid])['skills'],
                        'assessment_skill': knowledge.annotation(problems[pid]).get('assessment_skill'),
                        'kind': problems[pid].get('kind', 'exercise'),
                        'reflection_required': True, 'can_reveal': False,
                        'reflection_prompt': 'What do you notice? Describe a first step, a useful relationship, or what you are unsure about before choosing an answer.',
                        "has_hints": bool(content(pid)[1]), "has_solution": bool(content(pid)[2])}
            if path == "/api/problems":
                return {'version': 'connected-graph-v2', "sources": catalog.sources, "problems": [{"key": key, "id": p["id"], "skill": content(key)[0],
                         'skills': knowledge.annotation(p)['skills'], 'kind': p.get('kind', 'exercise'),
                         "language": p["language"], "format": catalog.public(key)["format"]} for key, p in problems.items()]}
            if path not in ("/api/answer", "/api/hint", "/api/solution", "/api/reveal", '/api/reflect'):
                raise ValueError("Unknown action")
            session = con.execute("SELECT * FROM sessions WHERE id=? AND student=?", (body.get("session"), student)).fetchone()
            if session is None:
                raise ValueError("Open a problem first")
            pid = session["problem"]
            if pid not in problems:
                raise ValueError("This problem is no longer loaded. Open another problem.")
            if path == '/api/reflect':
                reflection = body.get('reflection')
                if not isinstance(reflection, str) or not 5 <= len(reflection.strip()) <= 1200:
                    raise ValueError('Write a short thought or question (5–1200 characters) before choosing an answer.')
                con.execute('UPDATE sessions SET reflection=? WHERE id=?', (reflection.strip(), session['id']))
                return {'reflection_saved': True, 'message': 'Your thinking is saved. Explore the choices and test your idea.'}
            if path in ('/api/reveal', '/api/solution') and not can_reveal(session, pid):
                raise ValueError('First share your thinking, make two attempts, and try a hint when available. Then you can review the answer.')
            if path == "/api/reveal":
                label = problems[pid].get("label")
                if label not in list("ABCDE"):
                    raise ValueError("No official answer key is available for this problem.")
                con.execute("UPDATE sessions SET revealed=1 WHERE id=?", (session["id"],))
                return {"answer": label, "message": f"The official correct answer is {label}. Further attempts on this problem count as assisted practice."}
            if path == "/api/hint":
                hints, scope = knowledge.hints(problems[pid])
                if not hints:
                    return {"message": "Reviewed hints are not yet available for this dataset problem.", 'can_reveal': can_reveal(session, pid)}
                rung = min(session["hints"], len(hints) - 1)
                con.execute("UPDATE sessions SET hints=hints+1 WHERE id=?", (session["id"],))
                result = tutor.request(student, problems[pid], content(pid)[0], session['last_answer'], hints, rung, scope, reflection=session['reflection'])
                updated = dict(session, hints=session['hints'] + 1)
                return dict(result, can_reveal=can_reveal(updated, pid))
            if path == "/api/solution":
                if not content(pid)[2]:
                    return {"message": "A reviewed explanation is not yet available for this problem."}
                con.execute("UPDATE sessions SET revealed=1 WHERE id=?", (session["id"],))
                return {"message": content(pid)[2]}
            answer = body.get("answer")
            if not session['reflection']:
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
            evidence = student_model.record(con, student, session, problems[pid], knowledge.annotation(problems[pid]), correct,
                                            attempt_id, eligible, reason, knowledge)
            con.execute("UPDATE sessions SET tries=tries+1, solved=?, last_answer=? WHERE id=?", (int(correct), answer, session["id"]))
            message = ('Correct! Independent first-attempt success.' if independent else 'Correct! Recorded as assisted or repeat practice.') if correct else 'Not quite. Try a hint or a short skill check to find the next step.'
            if evidence['reason'] == 'multi_skill_requires_diagnostic':
                message += ' This problem combines skills; a short diagnostic will help identify what to practise.'
            return {"correct": correct, "message": message, 'evidence': evidence,
                    'can_reveal': can_reveal(dict(session, tries=session['tries'] + 1, solved=int(correct)), pid)}
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
    parser.add_argument('--local-tutor', action='store_true', help='Let the local SLM select from authored hints; stored fallback always available')
    args = parser.parse_args()
    try:
        catalog = Catalog(args.input or default_inputs(ROOT), args.images)
        knowledge = Knowledge(annotations=[args.annotations])
    except (OSError, ValueError) as error:
        parser.error(str(error))
    initialize(args.db)
    try:
        handler = make_handler(args.db, catalog, knowledge=knowledge, local_tutor=args.local_tutor)
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
