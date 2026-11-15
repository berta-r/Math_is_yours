"""Graph similarity is independent of prerequisite reasoning and student state."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from copilot.knowledge import Knowledge
from copilot.learning_graph import LearningGraph, build_path, validate_relations
from laptop.build_skill_graph import documents, keyword_vectors, make_relations


class GraphTests(unittest.TestCase):
    def setUp(self):
        self.knowledge = Knowledge()
        self.states = {sid:{'id':sid,'name':skill['title'],'state':'not_assessed','mastery':.2,
                            'evidence':0,'due':False,'next_review':None} for sid,skill in self.knowledge.skills.items()}

    def test_weak_goal_builds_prerequisites_without_lowering_strong_nodes(self):
        self.states['division'].update(state='developing',mastery=.13,evidence=1)
        self.states['arithmetic'].update(state='demonstrated',mastery=.95,evidence=4)
        before = copy.deepcopy(self.states)
        route = build_path(self.states,self.knowledge)
        self.assertEqual(route['goal'],'division')
        self.assertEqual([s['id'] for s in route['steps']],['multiplication','division'])
        self.assertEqual(route['next_skill'],'multiplication')
        self.assertEqual(route['strengths'][0]['id'],'arithmetic')
        self.assertEqual(self.states,before)

    def test_relatedness_never_invents_a_prerequisite(self):
        edges = [{'source':'spatial_reasoning','target':'division','weight':1,'kind':'semantic'}]
        route = build_path(self.states,self.knowledge,goal='division',related_edges=edges)
        self.assertEqual([s['id'] for s in route['steps']],['arithmetic','multiplication','division'])
        self.assertNotIn('spatial_reasoning',[s['id'] for s in route['steps']])

    def test_unknown_is_a_diagnostic_and_strength_can_anchor_exploration(self):
        route = build_path(self.states,self.knowledge)
        self.assertEqual(route['goal'],'arithmetic')
        self.assertIn('do not yet have independent evidence',route['steps'][0]['reason'])
        self.states['arithmetic'].update(state='demonstrated',mastery=.95,evidence=4)
        edges = [{'source':'arithmetic','target':'patterns','weight':.8,'kind':'semantic'}]
        self.assertEqual(build_path(self.states,self.knowledge,related_edges=edges)['goal'],'patterns')

    def test_due_strength_stays_demonstrated_and_gets_review(self):
        for state in self.states.values():
            state.update(state='demonstrated',mastery=.95,evidence=4)
        self.states['arithmetic'].update(due=True,next_review='2026-01-01')
        route = build_path(self.states,self.knowledge)
        self.assertEqual(route['goal'],'arithmetic')
        self.assertEqual(route['steps'][0]['state'],'demonstrated')
        self.assertTrue(route['steps'][0]['due'])

    def test_keyword_graph_is_deterministic_compact_and_explicit(self):
        texts = documents(self.knowledge)
        vectors = keyword_vectors(texts)
        a = make_relations(self.knowledge,vectors,'keyword-tfidf','Original skill text')
        b = make_relations(self.knowledge,vectors,'keyword-tfidf','Original skill text')
        self.assertEqual(a,b)
        self.assertTrue(a['related_edges'])
        self.assertNotIn('vectors',a)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'graph.json'
            path.write_text(json.dumps(a),encoding='utf-8')
            graph = LearningGraph(self.knowledge,path)
            self.assertEqual(graph.method,'keyword-tfidf')
            self.assertLess(path.stat().st_size,10000)

    def test_embedding_neighbors_follow_cosine_and_reject_malformed_vectors(self):
        vectors = {sid:[1.,0.] if sid in ['arithmetic','multiplication'] else [0.,1.] for sid in self.knowledge.skills}
        result = make_relations(self.knowledge,vectors,'embeddings','Invented vectors',neighbors=1,threshold=.5)
        self.assertIn({'source':'arithmetic','target':'multiplication','weight':1.,'kind':'semantic'},result['related_edges'])
        vectors['division'] = [float('nan'),1.]
        with self.assertRaises(ValueError):
            make_relations(self.knowledge,vectors,'embeddings','Bad vectors')

    def test_unknown_ids_self_edges_duplicates_and_nan_are_rejected(self):
        data = make_relations(self.knowledge,keyword_vectors(documents(self.knowledge)),'keyword-tfidf','Original')
        invalids = [dict(source='unknown',target='division',weight=.2,kind='semantic'),
                    dict(source='division',target='division',weight=.2,kind='semantic'),
                    dict(source='arithmetic',target='division',weight=float('nan'),kind='semantic'),
                    dict(source='arithmetic',target='division',weight=True,kind='semantic')]
        for edge in invalids:
            sample = dict(data,related_edges=[edge])
            with self.assertRaises(ValueError):
                validate_relations(sample,self.knowledge.skills)
        with self.assertRaises(ValueError):
            validate_relations(dict(data,related_edges=[data['related_edges'][0]]*2),self.knowledge.skills)

    def test_path_has_no_duplicate_steps_and_is_bounded(self):
        route = build_path(self.states,self.knowledge,goal='geometry_measurement')
        ids = [s['id'] for s in route['steps']]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertLessEqual(len(ids),6)
        self.assertEqual(ids[-1],'geometry_measurement')
        self.assertLess(ids.index('arithmetic'),ids.index('multiplication'))
        self.assertLess(ids.index('multiplication'),ids.index('division'))


if __name__ == '__main__':
    unittest.main()
