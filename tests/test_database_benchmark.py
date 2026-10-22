"""Comparison evidence must use equivalent facts and detect changing results."""
from copy import deepcopy
import unittest

from scripts.benchmark_databases import compare, fingerprint, mongo_rows, run, sql_rows


class DatabaseBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.sql = [dict(battle_id='fixture', trainer_id=1, owned_id=2, pokemon_id=25, is_shiny=0)]
        self.mongo = [dict(_id='fixture', trainer_id=1, reward=dict(owned_id=2, pokemon_id=25))]
        self.expected = sql_rows(self.sql)

    def test_order_and_legacy_shiny_representation_do_not_change_comparison(self):
        self.assertEqual(self.expected, mongo_rows(self.mongo))
        self.assertEqual(fingerprint(self.expected), fingerprint(mongo_rows(self.mongo)))
        calls = []

        def sql():
            calls.append('sql')
            return self.sql

        def mongo():
            calls.append('mongo')
            return self.mongo

        result = compare(sql, mongo, self.expected, samples=3)
        self.assertEqual(calls, ['sql','mongo','sql','mongo','mongo','sql','sql','mongo'])
        for values in result.values():
            self.assertEqual(len(values['samples_seconds']), 3)

    def test_disagreeing_awards_reject_the_comparison(self):
        changed = deepcopy(self.mongo)
        changed[0]['reward']['pokemon_id'] = 4
        with self.assertRaisesRegex(ValueError, 'same award facts'):
            compare(lambda:self.sql, lambda:changed, self.expected, samples=3)

    def test_changed_sample_is_not_presented_as_a_valid_timing(self):
        reads = iter([self.mongo, []])
        with self.assertRaisesRegex(ValueError, 'results changed'):
            compare(lambda:self.sql, lambda:next(reads), self.expected, samples=3)

    def test_empty_cohort_or_unbounded_workload_is_rejected(self):
        with self.assertRaises(ValueError):
            compare(lambda:[], lambda:[], [])
        for samples, limit in [(0,100),(31,100),(7,0),(7,501)]:
            with self.subTest(samples=samples, limit=limit), self.assertRaises(ValueError):
                run(samples=samples,limit=limit)


if __name__ == '__main__':
    unittest.main()
