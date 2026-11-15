"""Laptop preparation uses invented vectors/text and requires explicit review."""
import argparse
import csv
import json
import tempfile
import unittest
from pathlib import Path

from laptop.annotate_problems import cluster, export_review, kmeans


class AnnotationTests(unittest.TestCase):
    def test_kmeans_is_repeatable_and_rejects_malformed_vectors(self):
        vectors = [[1., 0.], [0.9, .1], [0., 1.], [.1, .9]]
        labels, centers = kmeans(vectors, 2)
        self.assertEqual((labels, centers), kmeans(vectors, 2))
        self.assertEqual(labels[0], labels[1])
        self.assertEqual(labels[2], labels[3])
        self.assertNotEqual(labels[0], labels[2])
        for invalid in [[], [[1.], [1., 2.]], [[float('nan')]], [[]]]:
            with self.assertRaises(ValueError):
                kmeans(invalid, 1)

    def test_english_canonical_ids_and_only_reviewed_rows_export(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root/'input.jsonl'
            rows = [{'id':'one','language':'eng','text':'Count equal groups'},
                    {'id':'one','language':'cat','text':'Compta grups iguals'},
                    {'id':'two','language':'eng','text':'Rotate a shape'}]
            source.write_text('\n'.join(json.dumps(row) for row in rows), encoding='utf-8')
            args = argparse.Namespace(input=source,features='tfidf',out=root/'clusters',clusters=2,overwrite=False)
            cluster(args)
            result = json.loads((args.out/'clusters.json').read_text(encoding='utf-8'))
            self.assertEqual(set(result['assignments']), {'one','two'})
            self.assertNotIn('skills', result)
            with self.assertRaisesRegex(ValueError, 'already exists'):
                cluster(args)
            review = args.out/'cluster-review.csv'
            with review.open(encoding='utf-8',newline='') as stream:
                reader = csv.DictReader(stream)
                fields, reviewed = reader.fieldnames, list(reader)
            reviewed[0].update(status='reviewed', reviewer='Test reviewer', skills='multiplication', assessment_skill='multiplication')
            with review.open('w',encoding='utf-8',newline='') as stream:
                writer = csv.DictWriter(stream,fieldnames=fields)
                writer.writeheader()
                writer.writerows(reviewed)
            output = root/'annotations.json'
            export_review(argparse.Namespace(review=review,output=output))
            accepted = json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(set(accepted['problems']), {'one'})
            self.assertEqual(accepted['problems']['one']['assessment_skill'], 'multiplication')
            reviewed[0]['status'] = 'pending'
            with review.open('w',encoding='utf-8',newline='') as stream:
                writer = csv.DictWriter(stream,fieldnames=fields)
                writer.writeheader()
                writer.writerows(reviewed)
            export_review(argparse.Namespace(review=review,output=output))
            self.assertEqual(json.loads(output.read_text(encoding='utf-8'))['problems'], {})


if __name__ == '__main__':
    unittest.main()
