"""
Runs the contention benchmark at a tiny size so that it keeps working as the repository changes.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'benchmark'))

from bench_contention import SCENARIOS, run_scenario
from bench_ladder import parse_config

from helpers import slow


class TestBenchmarkSmoke(unittest.TestCase):
    """
    The benchmark scenarios run and report no integrity problem.
    """

    @slow
    def test_every_scenario_keeps_integrity(self):
        """Every scenario finishes with no failed expectation and a clean disk audit."""
        for scenario in SCENARIOS:
            summary = run_scenario(scenario, 3, 2, 1, 200, False)
            self.assertEqual(summary['failures'], 0, summary['failure_samples'])
            self.assertEqual(summary['disk_problems'], {})

    def test_sizes_are_read_as_processes_by_threads(self):
        """A size is read as processes x threads and anything else is refused."""
        self.assertEqual(parse_config('500x10'), (500, 10))
        self.assertEqual(parse_config('1X1'), (1, 1))
        for text in ('10', '0x5', 'axb', '1x2x3', '-1x2'):
            with self.assertRaises(ValueError):
                parse_config(text)


if __name__ == '__main__':
    unittest.main()
