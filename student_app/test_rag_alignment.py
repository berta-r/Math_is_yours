"""ALIGN_CATALAN flag in the RAG index (T-105): off changes nothing, on maps Catalan queries."""
import json
import sqlite3
import tempfile
import unittest
from array import array
from pathlib import Path
from unittest.mock import patch

from copilot import rag
from copilot.alignment import Alignment
from copilot.config import load

# W swaps the first two axes: a Catalan query along x is mapped onto y.
MATRIX = [[0.0, 1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]
QUERY = [1.0, 0.0, 0.0]


class AlignmentFlagTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        folder = Path(self.temp.name)
        self.procrustes = folder / 'procrustes.json'
        self.procrustes.write_text(json.dumps({'version': 1, 'method': 'orthogonal-procrustes', 'dimensions': 3, 'matrix': MATRIX}))
        self.db = folder / 'index.db'
        con = sqlite3.connect(self.db)
        con.execute(rag.SCHEMA)
        for pid, vec in (('x', [1.0, 0.0, 0.0]), ('y', [0.0, 1.0, 0.0])):
            con.execute('INSERT INTO problems VALUES (?,?,?)', (f'{pid}|eng', json.dumps({'id': pid, 'language': 'eng'}),
                                                                 array('f', vec).tobytes()))
        con.commit()
        con.close()

    def tearDown(self):
        self.temp.cleanup()

    def search(self, index, language):
        problem = {'id': 'q', 'language': language, 'text': 't', 'options': {}}
        with patch.object(rag, 'embed', return_value=[list(QUERY)]):
            return index.query_vector(problem), index.search(problem, k=1)[0][1]['id']

    def test_flag_is_off_by_default(self):
        self.assertEqual(load()['ALIGN_CATALAN'], '0')
        self.assertFalse(rag.Index(self.db).align_catalan)

    def test_off_leaves_the_query_unchanged(self):
        index = rag.Index(self.db, align_catalan=False, alignment=Alignment(self.procrustes))
        self.assertEqual(self.search(index, 'cat'), (QUERY, 'x'))

    def test_on_maps_catalan_only(self):
        index = rag.Index(self.db, align_catalan=True, alignment=Alignment(self.procrustes))
        vector, hit = self.search(index, 'cat')
        self.assertEqual((vector, hit), ([0.0, 1.0, 0.0], 'y'))
        self.assertEqual(self.search(index, 'eng'), (QUERY, 'x'))

    def test_on_without_matrix_file_is_unchanged(self):
        index = rag.Index(self.db, align_catalan=True, alignment=Alignment(Path(self.temp.name) / 'absent.json'))
        self.assertEqual(self.search(index, 'cat'), (QUERY, 'x'))


if __name__ == '__main__':
    unittest.main()
