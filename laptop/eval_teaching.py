"""Compare selectors with synthetic students, not an educational efficacy study.

Original diagnostic fixtures only. Static response probabilities; no simulated
learning gain. Times measure this laptop's Python selector, not board/model time.
"""
import argparse
import json
import random
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from copilot.knowledge import Knowledge
from copilot import scheduler, student_model
from student_app import server as app


def compare(students=30, steps=20, seed=42):
    knowledge = Knowledge()
    catalog = app.Catalog([ROOT/'data/sample_problems.jsonl'], ROOT/'data/images')
    for problem in knowledge.diagnostics:
        catalog.problems[problem['id']+'|'+problem['language']] = problem
    skill_ids = list(knowledge.skills)
    rows = []
    for policy in ('adaptive', 'random', 'correct_harder'):
        times, suitable, fresh, total, coverages = [], 0, 0, 0, []
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder)/'simulation.db'
            app.initialize(db)
            with app.connection(db) as con:
                con.row_factory = sqlite3.Row
                for learner in range(students):
                    student = f'synthetic-{learner}'
                    rng = random.Random(seed + learner)
                    weak = skill_ids[learner % len(skill_ids)]
                    target = {weak, *knowledge.skills[weak]['prerequisites']}
                    seen, practised, focus = set(), set(), None
                    current = next(p for p in knowledge.diagnostics if p['assessment_skill'] == weak)
                    last_correct = False
                    for step in range(steps + 1):
                        started = time.perf_counter()
                        return_to = None
                        if step:
                            if policy == 'adaptive':
                                rec = scheduler.recommend(con, student, catalog, knowledge, focus=focus)
                                if not rec['problem']:
                                    break
                                current = catalog.problems[rec['problem']]
                                return_to = rec.get('return_to')
                            else:
                                candidates = [p for p in catalog.problems.values() if p['id'] not in seen]
                                if not candidates:
                                    break
                                if policy == 'correct_harder':
                                    level = max(0, int(current.get('level') or 0) + (1 if last_correct else -1))
                                    distance = min(abs(int(p.get('level') or 0)-level) for p in candidates)
                                    candidates = [p for p in candidates if abs(int(p.get('level') or 0)-level) == distance]
                                current = rng.choice(candidates)
                            times.append((time.perf_counter()-started)*1000)
                        tag = knowledge.annotation(current)
                        skills = set(tag['skills'])
                        if step:
                            total += 1
                            suitable += bool(skills & target)
                            fresh += current['id'] not in seen
                            practised.update(skills)
                        # All policies start with the same observed failed diagnostic.
                        probability = min((.25 if sid == weak else .4 if sid in target else .85 for sid in skills), default=.5)
                        correct = False if step == 0 else rng.random() < probability
                        focus = f'{student}-{step}'
                        key = current['id']+'|'+current['language']
                        now = student_model.utc_now()
                        con.execute('INSERT INTO sessions(id,student,problem,started_at,return_to) VALUES(?,?,?,?,?)', (focus, student, key, now, return_to))
                        session = con.execute('SELECT * FROM sessions WHERE id=?', (focus,)).fetchone()
                        eligible = current['id'] not in seen
                        answer = current['label'] if correct else next(c for c in 'ABCDE' if c != current['label'])
                        attempt = con.execute('INSERT INTO attempts(student,problem,answer,correct,independent) VALUES(?,?,?,?,?)', (student,key,answer,int(correct),int(eligible and correct))).lastrowid
                        student_model.record(con, student, session, current, tag, correct, attempt, eligible,
                                             'independent_first_attempt' if eligible else 'repeat_or_translation', knowledge, now)
                        con.execute('UPDATE sessions SET tries=1,solved=?,last_answer=? WHERE id=?', (int(correct),answer,focus))
                        seen.add(current['id'])
                        last_correct = correct
                    coverages.append(len(practised))
        rows.append({'policy':policy,'recommendations':total,'weak_or_supporting_skill_fraction':round(suitable/max(total,1),3),
                     'fresh_fraction':round(fresh/max(total,1),3),'mean_skills_practised':round(sum(coverages)/students,2),
                     'selector_ms_mean':round(sum(times)/max(len(times),1),3),'selector_ms_worst':round(max(times,default=0),3)})
    return {'seed':seed, 'students':students, 'max_steps':steps,
            'conditions':'Static synthetic ability. One seeded failed diagnostic per learner. Original fixtures only. Correct-harder uses grade categories with random ties; most diagnostics share level 0. Suitability is a declared weak/supporting-tag proxy, not a learning outcome. CPU times are laptop-only.',
            'results':rows}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--students', type=int, default=30)
    parser.add_argument('--steps', type=int, default=20)
    parser.add_argument('--output', type=Path, default=ROOT/'results/teaching-simulation.json')
    args = parser.parse_args()
    if args.students < 1 or args.steps < 1:
        parser.error('students and steps must be positive')
    report = compare(args.students, args.steps)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
