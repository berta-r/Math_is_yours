"""A retrieval index in SQLite: one solved M3Kang problem per row."""
import json
import sqlite3
from array import array

from .alignment import Alignment
from .config import CONFIG
from .embed import embed
from .llm import format_problem

SCHEMA = """
CREATE TABLE IF NOT EXISTS problems (
    key TEXT PRIMARY KEY,   -- id|language
    problem TEXT NOT NULL,  -- the full problem as JSON
    vec BLOB NOT NULL       -- float32 vector
)"""


def build(db_path, problems, batch=16):
    db = sqlite3.connect(db_path)
    db.execute(SCHEMA)
    for i in range(0, len(problems), batch):
        chunk = problems[i:i + batch]
        vectors = embed([format_problem(p) for p in chunk])
        db.executemany("INSERT OR REPLACE INTO problems VALUES (?, ?, ?)", [
            (f"{p['id']}|{p['language']}", json.dumps(p, ensure_ascii=False), array("f", v).tobytes())
            for p, v in zip(chunk, vectors)])
        db.commit()
        yield min(i + batch, len(problems))
    db.close()


class Index:
    """Loads every vector into memory once, so each search is a plain loop."""

    def __init__(self, db_path, align_catalan=None, alignment=None):
        """align_catalan: rotate Catalan queries with Procrustes W (default: ALIGN_CATALAN in config.env)."""
        if align_catalan is None:
            align_catalan = CONFIG.get("ALIGN_CATALAN", "0").strip() == "1"
        self.align_catalan = align_catalan
        self._alignment = alignment
        db = sqlite3.connect(db_path)
        self.rows = []
        for key, problem, blob in db.execute("SELECT key, problem, vec FROM problems"):
            vec = array("f")
            vec.frombytes(blob)
            self.rows.append((key, json.loads(problem), vec))
        db.close()

    def query_vector(self, problem):
        """Embedded query; Catalan ones are mapped into English space when the flag is on."""
        query = embed([format_problem(problem)], query=True)[0]
        if self.align_catalan and problem.get("language") == "cat":
            if self._alignment is None:
                self._alignment = Alignment()  # loaded once, on the first Catalan query
            if self._alignment.enabled:
                query = self._alignment.apply(query)
        return query

    def search(self, problem, k=1, exclude_id=None):
        """Return up to k (score, problem) pairs, most similar first.

        exclude_id skips the same problem in other languages, so validation
        never retrieves its own translation.
        """
        query = self.query_vector(problem)
        scored = []
        for _key, stored, vec in self.rows:
            if exclude_id and stored["id"] == exclude_id:
                continue
            scored.append((sum(a * b for a, b in zip(query, vec)), stored))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return scored[:k]
