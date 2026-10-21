"""
Tests of the attempts an operation makes when it fails: which errors are attempted again, the pauses, and the messages.
"""
import os
import errno
import time
import unittest
import importlib
from unittest import mock

from pyrep import Repository

from helpers import TemporaryRepository, audit_repository

module = importlib.import_module('pyrep.Repository')


class TestTransientErrors(unittest.TestCase):
    """
    Which errors are worth another attempt, how long the pauses are, and how attempts are described.
    """

    def test_errors_that_can_pass_by_themselves_are_transient(self):
        """Busy, interrupted, temporarily unavailable, timed out and stale handle errors are transient."""
        for number in (errno.EINTR, errno.EAGAIN, errno.EBUSY, errno.ETIMEDOUT, errno.EMFILE):
            self.assertTrue(module.is_transient_error(OSError(number, 'transient')), number)
        for error in (InterruptedError(), BlockingIOError(), TimeoutError()):
            self.assertTrue(module.is_transient_error(error), type(error).__name__)

    def test_other_errors_are_permanent(self):
        """Missing files, full disks, bad values and plain exceptions are never attempted again."""
        for error in (OSError(errno.ENOENT, 'missing'), OSError(errno.ENOSPC, 'full'), OSError(errno.EEXIST, 'exists'),
                      ValueError('bad'), KeyError('k'), Exception('plain'), FileNotFoundError(), IsADirectoryError()):
            self.assertFalse(module.is_transient_error(error), repr(error))

    @unittest.skipIf(os.name == 'nt', 'a refused access is transient on Windows')
    def test_a_refused_access_is_permanent_on_posix(self):
        """On POSIX systems a refused access is a permission problem and does not pass by itself."""
        self.assertFalse(module.is_transient_error(PermissionError(errno.EACCES, 'denied')))

    def test_a_wrapped_transient_error_is_found_and_a_cycle_is_safe(self):
        """The error an operation wrapped is looked at, and a chain that loops does not hang."""
        wrapper = Exception('Unable to open repository file')
        wrapper.__cause__ = OSError(errno.EBUSY, 'busy')
        self.assertTrue(module.is_transient_error(wrapper))
        first, second = Exception('a'), Exception('b')
        first.__cause__, second.__cause__ = second, first
        self.assertFalse(module.is_transient_error(first))

    def test_pauses_double_with_every_attempt_and_stay_bounded(self):
        """The pause before attempt n+1 is between half and the whole of the doubled base delay, up to the maximum."""
        recorded = []
        transient = OSError(errno.EBUSY, 'busy')
        with mock.patch.object(module.time, 'sleep', side_effect=recorded.append):
            for trial in range(3):
                self.assertTrue(module.should_retry(transient, trial, 10))
            self.assertTrue(module.should_retry(transient, 9 - 1, 10))
        for trial, delay in enumerate(recorded[:3]):
            full = module.RETRY_BASE_DELAY * 2 ** trial
            self.assertTrue(full / 2 <= delay <= full, (trial, delay))
        self.assertTrue(module.RETRY_MAX_DELAY / 2 <= recorded[3] <= module.RETRY_MAX_DELAY)

    def test_no_attempt_follows_the_last_one_or_a_permanent_error(self):
        """The last attempt and permanent errors end the operation without any pause."""
        with mock.patch.object(module.time, 'sleep') as sleep:
            self.assertFalse(module.should_retry(OSError(errno.EBUSY, 'busy'), 2, 3))
            self.assertFalse(module.should_retry(OSError(errno.EBUSY, 'busy'), 0, 1))
            self.assertFalse(module.should_retry(ValueError('bad'), 0, 3))
        sleep.assert_not_called()

    def test_attempts_are_described_one_by_one(self):
        """One error is shown as it is, several are numbered."""
        self.assertEqual(module.describe_attempts(['only']), 'only')
        self.assertEqual(module.describe_attempts(['a', 'b', 'c']), 'attempt 1: a; attempt 2: b; attempt 3: c')


class TestAttemptsInOperations(unittest.TestCase):
    """
    The same rules seen from the operations, with user code and with injected file system errors.
    """

    def setUp(self):
        self.temporary = TemporaryRepository(timeout=3)
        self.temporary.__enter__()
        self.addCleanup(self.temporary.__exit__, None, None, None)
        self.repo    = self.temporary.repo
        self.counter = os.path.join(self.temporary.root, 'calls.txt')

    def calls(self):
        """
        The number of times the test code ran.
        """
        return len(open(self.counter).read()) if os.path.exists(self.counter) else 0

    def failing_dump(self, kind):
        """
        Source of a dump method that counts its runs and fails with the given error.
        """
        return ("import errno\ndef dump(path, value):\n    open(%r, 'a').write('x')\n    raise %s\n"%(self.counter, kind))

    def test_a_permanent_error_of_a_dump_method_is_not_attempted_again(self):
        """A dump method that fails for good runs once, even though three attempts are allowed."""
        succeeded, message = self.repo.dump_file('v', 'name', dump=self.failing_dump("ValueError('permanent')"), raiseError=False)
        self.assertFalse(succeeded)
        self.assertEqual(self.calls(), 1)
        self.assertNotIn('attempt 1', message)

    def test_a_transient_error_is_attempted_again_with_a_pause_and_every_error_is_reported(self):
        """A dump method that keeps failing with a busy error runs three times, after pauses, and the message lists all three."""
        start = time.time()
        succeeded, message = self.repo.dump_file('v', 'name', dump=self.failing_dump("OSError(errno.EBUSY, 'device busy')"), raiseError=False)
        self.assertFalse(succeeded)
        self.assertEqual(self.calls(), 3)
        self.assertGreaterEqual(time.time() - start, module.RETRY_BASE_DELAY * 1.5 - 0.001)
        for number in (1, 2, 3):
            self.assertIn('attempt %i'%number, message)
        self.assertEqual(list(self.repo.walk_files_path(recursive=True)), [])

    def test_one_attempt_means_no_pause_and_no_second_run(self):
        """ntrials=1 runs the code once and reports its error as it is."""
        succeeded, message = self.repo.dump_file('v', 'name', dump=self.failing_dump("OSError(errno.EBUSY, 'device busy')"), raiseError=False, ntrials=1)
        self.assertFalse(succeeded)
        self.assertEqual(self.calls(), 1)
        self.assertNotIn('attempt 1', message)

    def test_a_flaky_pull_method_succeeds_when_enough_attempts_are_allowed(self):
        """A pull method that is busy twice and then works succeeds with three attempts and fails with two."""
        self.repo.dump_file('stored', 'name')
        pull = ("import errno, os\ndef pull(path):\n    n = len(open(%r).read()) if os.path.exists(%r) else 0\n"
                "    open(%r, 'a').write('x')\n    if n < 2:\n        raise OSError(errno.EBUSY, 'busy')\n    return 'worked after %%i failures'%%n\n"%(self.counter, self.counter, self.counter))
        with self.assertRaises(Exception) as caught:
            self.repo.pull_file('name', pull=pull, ntrials=2)
        self.assertIn('attempt 2', str(caught.exception))
        os.remove(self.counter)
        self.assertEqual(self.repo.pull_file('name', pull=pull, ntrials=3), 'worked after 2 failures')

    def test_an_update_survives_a_busy_file_system_and_fails_cleanly_when_it_stays_busy(self):
        """A busy error while moving files is attempted again, and when it lasts the old value stays and nothing is left behind."""
        self.repo.dump_file('old value', 'name')
        realReplace = os.replace

        def busy_for(count):
            state = {'left': count}

            def replace(source, destination):
                if state['left'] > 0:
                    state['left'] -= 1
                    raise OSError(errno.EBUSY, 'busy')
                return realReplace(source, destination)

            return replace

        with mock.patch.object(os, 'replace', side_effect=busy_for(2)):
            self.assertEqual(self.repo.update_file('new value', 'name'), (True, ''))
        self.assertEqual(self.repo.pull_file('name'), 'new value')
        with mock.patch.object(os, 'replace', side_effect=busy_for(10)):
            succeeded, message = self.repo.update_file('newer value', 'name', raiseError=False)
        self.assertFalse(succeeded)
        self.assertIn('attempt 3', message)
        self.assertEqual(self.repo.pull_file('name'), 'new value')
        self.assertEqual(audit_repository(self.temporary.path), {})


if __name__ == '__main__':
    unittest.main()
