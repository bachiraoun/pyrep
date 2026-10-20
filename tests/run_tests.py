"""Runs every test of pyrep and prints a short summary, the same way on every machine.

Usage::

    python3 tests/run_tests.py                       ## everything, one line for each test
    python3 tests/run_tests.py --quiet               ## only the summary
    python3 tests/run_tests.py --quick               ## everything except the slow crash and lock server tests
    python3 tests/run_tests.py --scale 3             ## three times more operations in the concurrency tests
    python3 tests/run_tests.py --repeat 5            ## five times, to find a test that sometimes fails
    python3 tests/run_tests.py safety regressions    ## only tests/test_safety.py and tests/test_regressions.py
    python3 tests/run_tests.py --list                ## the test files

Every test prints one line, ``PASS``, ``FAIL``, ``ERROR`` or ``SKIP`` with the seconds it took and its name, then a summary by
test file, the known bugs that are still open, the details of what failed, and the totals. A test that is expected to fail
because of a known bug prints ``PASS`` with the bug in brackets. The exit code is 0 when every test passed and 1 otherwise.
"""
import argparse
import os
import platform
import sys
import time
import traceback
import unittest

TESTS_FOLDER = os.path.dirname(os.path.abspath(__file__))


def find_test_files():
    """
    Lists the test modules of the folder.

    :Returns:
        #. names (list): Module names without the test_ prefix, in alphabetical order.
    """
    return sorted(name[5:-3] for name in os.listdir(TESTS_FOLDER) if name.startswith('test_') and name.endswith('.py'))


def load_suite(names):
    """
    Loads the tests of the named modules.

    :Parameters:
        #. names (list): Module names without the test_ prefix.

    :Returns:
        #. suite (unittest.TestSuite): One suite with all the tests.
    """
    loader = unittest.TestLoader()
    sys.path.insert(0, TESTS_FOLDER)
    suite = unittest.TestSuite()
    for name in names:
        suite.addTests(loader.loadTestsFromName(f'test_{name}'))
    return suite


def known_bug_summary(test):
    """
    Reads the summary given to the known_bug marker of a test.

    :Parameters:
        #. test (unittest.TestCase): The test.

    :Returns:
        #. summary (str): The summary of the bug, or a placeholder when there is none.
    """
    return getattr(getattr(test, test._testMethodName), 'knownBug', 'no summary')


class LineResult(unittest.TestResult):
    """
    A test result that prints one line for each test, and keeps what every test did for the summary.
    The output of a test is held back while it runs, and shown with the details of a test that failed.

    :Parameters:
        #. isQuiet (bool): True to print no line for the tests, only the summary at the end.
    """

    def __init__(self, isQuiet):
        super().__init__()
        self.buffer      = True
        self.isQuiet     = isQuiet
        self.outcomes    = []
        self.knownBugs   = []
        self.__started   = 0.0

    def startTest(self, test):
        super().startTest(test)
        self.__started = time.monotonic()

    @staticmethod
    def last_line(err):
        """
        Shortens an exception to its last line, such as AssertionError: 1 != 2.

        :Parameters:
            #. err (tuple): The exception type, value and traceback.

        :Returns:
            #. line (str): The last line of the exception, at most 160 characters.
        """
        return traceback.format_exception_only(err[0], err[1])[-1].strip()[:160]

    def record(self, name, outcome, detail=''):
        """
        Keeps the outcome of a test and prints its line straight to the terminal, because the test holds back its own output.

        :Parameters:
            #. name (str): The test id.
            #. outcome (str): One of PASS, FAIL, ERROR or SKIP.
            #. detail (str): Text printed in brackets after the name.
        """
        seconds = time.monotonic() - self.__started
        self.outcomes.append((name, outcome, seconds))
        if not self.isQuiet:
            sys.__stdout__.write(f"{outcome:5s} {seconds:7.3f}s  {name}{'  (' + detail + ')' if detail else ''}\n")
            sys.__stdout__.flush()

    def addSuccess(self, test):
        super().addSuccess(test)
        self.record(test.id(), 'PASS')

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.record(test.id(), 'FAIL', self.last_line(err))

    def addError(self, test, err):
        super().addError(test, err)
        self.record(test.id(), 'ERROR', self.last_line(err))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.record(test.id(), 'SKIP', reason)

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self.knownBugs.append((test.id(), known_bug_summary(test)))
        self.record(test.id(), 'PASS', f'known bug: {known_bug_summary(test)}')

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.record(test.id(), 'FAIL', 'the known bug is fixed, remove its @known_bug marker')


def print_summary(result):
    """
    Prints the results by test file, the known bugs, the names of what failed, their details, and the skipped tests.

    :Parameters:
        #. result (LineResult): The finished result.
    """
    byFile = {}
    for name, outcome, taken in result.outcomes:
        counts = byFile.setdefault(name.split('.')[0], {'PASS': 0, 'FAIL': 0, 'ERROR': 0, 'SKIP': 0, 'seconds': 0.0})
        counts[outcome] += 1
        counts['seconds'] += taken
    print(f"\n{'test file':32s} {'passed':>7s} {'failed':>7s} {'errors':>7s} {'skipped':>8s} {'seconds':>8s}")
    for fileName in sorted(byFile):
        counts = byFile[fileName]
        print(f"{fileName:32s} {counts['PASS']:7d} {counts['FAIL']:7d} {counts['ERROR']:7d} {counts['SKIP']:8d} {counts['seconds']:8.1f}")
    if len(result.knownBugs) > 0:
        print(f'\nknown bugs still open ({len(result.knownBugs)}):')
        for name, summary in result.knownBugs:
            print(f"  {name.split('.', 1)[-1]}\n      {summary}")
    failed = [(name, outcome) for name, outcome, _ in result.outcomes if outcome in ('FAIL', 'ERROR')]
    if len(failed) > 0:
        print('\nfailed tests:')
        for name, outcome in failed:
            print(f"  {outcome:5s} {name}")
    for kind, entries in (('FAILURES', result.failures), ('ERRORS', result.errors)):
        for test, details in entries:
            print(f"\n{'=' * 70}\n{kind[:-1]}: {test}\n{'-' * 70}\n{details.rstrip()}")
    for test, reason in result.skipped:
        print(f"skipped {test.id()}: {reason}")


def run_once(names, isQuiet):
    """
    Runs the tests once, prints a line for each and the summary.

    :Parameters:
        #. names (list): Module names without the test_ prefix.
        #. isQuiet (bool): True to print only the summary.

    :Returns:
        #. result (LineResult): The finished result.
        #. seconds (float): How long the run took.
    """
    started = time.monotonic()
    result  = LineResult(isQuiet)
    load_suite(names).run(result)
    seconds = time.monotonic() - started
    print_summary(result)
    return result, seconds


def main():
    """
    Parses the command line, runs the tests and returns the exit code.

    :Returns:
        #. exitCode (int): 0 when every run passed, 1 when a test failed, 2 for a wrong command line.
    """
    parser = argparse.ArgumentParser(description='Run the tests of pyrep.')
    parser.add_argument('names', nargs='*', help='test files to run, without test_ and .py, all when none is given')
    parser.add_argument('--repeat', type=int, default=1, help='number of times to run, to find tests that fail sometimes')
    parser.add_argument('--list', action='store_true', help='print the test files and stop')
    parser.add_argument('--quiet', action='store_true', help='print only the summary, not a line for each test')
    parser.add_argument('--quick', action='store_true', help='skip the slow crash and lock server tests')
    parser.add_argument('--scale', type=int, default=1, help='multiplier of the operations done by the concurrency tests')
    arguments = parser.parse_args()
    available = find_test_files()
    if arguments.list:
        print('\n'.join(available))
        return 0
    unknown = [name for name in arguments.names if name not in available]
    if len(unknown) > 0:
        print(f"unknown test files: {', '.join(unknown)}. Available: {', '.join(available)}")
        return 2
    if arguments.repeat < 1 or arguments.scale < 1:
        print('--repeat and --scale must be at least 1')
        return 2
    # The tests read these at import time, so they must be set before the modules are loaded
    os.environ['PYREP_TEST_QUICK'] = '1' if arguments.quick else '0'
    os.environ['PYREP_TEST_SCALE'] = str(arguments.scale)
    import pyrep
    import pylocker
    names = arguments.names if len(arguments.names) > 0 else available
    print(f"Python {platform.python_version()} on {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"pyrep {pyrep.get_version()} from {os.path.dirname(pyrep.__file__)}, pylocker {pylocker.__version__}")
    failedRuns = 0
    openBugs   = 0
    for number in range(1, arguments.repeat + 1):
        result, seconds = run_once(names, arguments.quiet)
        isGood      = result.wasSuccessful()
        failedRuns += 0 if isGood else 1
        openBugs    = len(result.knownBugs)
        print(f"run {number}/{arguments.repeat}: {result.testsRun} tests in {seconds:.1f}s, "
              f"{len(result.failures)} failed, {len(result.errors)} errors, {len(result.skipped)} skipped "
              f"-> {'PASS' if isGood else 'FAIL'}")
    # A passing run still has known bugs, so the last line says how many, or they would be easy to forget
    passed = f'ALL RUNS PASSED ({openBugs} known bugs still open)' if openBugs > 0 else 'ALL RUNS PASSED'
    print(passed if failedRuns == 0 else f'{failedRuns} RUN(S) FAILED')
    return 0 if failedRuns == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
