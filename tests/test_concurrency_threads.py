"""
Threads of one process fighting over the same repository, through one shared instance and through one instance per thread.
"""
import time
import threading
import unittest

from pyrep import Repository

from helpers import (SCALE, LOCK_TIMEOUT, TemporaryRepository, audit_repository, check_record, describe,
                     fight_expected_files, fight_for_files, make_record, run_in_threads)

THREAD_COUNT = 8
STEPS        = 10 * SCALE


class TestThreadsFightingForFiles(unittest.TestCase):
    """
    Every thread writes, updates and reads files with data only it could have produced.
    """

    def setUp(self):
        self.temporary = TemporaryRepository()
        self.temporary.__enter__()
        self.addCleanup(self.temporary.__exit__, None, None, None)
        self.repo = self.temporary.repo
        self.repo.dump_file(make_record('seed', 0, size=30000), 'shared/hot')
        self.writerIds = [f'thread{index}' for index in range(THREAD_COUNT)]

    def run_fight(self, makeRepo):
        """
        Runs one session per thread and checks the result from disk.
        """
        failures = []

        def session(writerId):
            repo = makeRepo()
            failures.extend(fight_for_files(repo, writerId, STEPS))

        crashes = run_in_threads(session, [(writerId,) for writerId in self.writerIds])
        self.assertEqual(crashes, [])
        self.assertEqual(failures, [], describe(failures))
        expected = fight_expected_files(self.writerIds, STEPS)
        problems = audit_repository(self.temporary.path, expectedFiles=expected)
        self.assertEqual(problems, {}, describe(problems))

    def test_threads_sharing_one_instance(self):
        """Several threads using the very same Repository object stay consistent."""
        self.run_fight(lambda: self.repo)

    def test_threads_with_their_own_instance(self):
        """Several threads each with their own Repository object stay consistent."""
        instances = []

        def make():
            instance = Repository(self.temporary.path, timeout=LOCK_TIMEOUT)
            instances.append(instance)
            return instance

        try:
            self.run_fight(make)
        finally:
            for instance in instances:
                instance.close()


class TestThreadsRacing(unittest.TestCase):
    """
    Threads released at the same moment on the same names.
    """

    def setUp(self):
        self.temporary = TemporaryRepository()
        self.temporary.__enter__()
        self.addCleanup(self.temporary.__exit__, None, None, None)
        self.repo = self.temporary.repo

    def test_same_name_has_exactly_one_winner(self):
        """When all threads dump the same new name, exactly one succeeds and its value is the stored one."""
        barrier = threading.Barrier(THREAD_COUNT)
        outcomes = []

        def contender(index):
            barrier.wait()
            succeeded, message = self.repo.dump_file(make_record(f'writer{index}', 0), 'race/name', raiseError=False)
            outcomes.append((index, succeeded, message))

        self.assertEqual(run_in_threads(contender, [(index,) for index in range(THREAD_COUNT)]), [])
        winners = [index for index, succeeded, _ in outcomes if succeeded]
        self.assertEqual(len(winners), 1, describe(outcomes))
        stored = self.repo.pull_file('race/name')
        self.assertTrue(check_record(stored)[0])
        self.assertEqual(stored['writer'], f'writer{winners[0]}')

    def test_same_directory_is_registered_once(self):
        """Adding the same directory from many threads tracks it once and succeeds for everybody."""
        barrier = threading.Barrier(THREAD_COUNT)
        outcomes = []

        def contender():
            barrier.wait()
            outcomes.append(self.repo.add_directory('same/deep/dir', raiseError=False)[0])

        self.assertEqual(run_in_threads(contender, [()] * THREAD_COUNT), [])
        self.assertEqual(outcomes, [True] * THREAD_COUNT)
        self.assertEqual(sorted(self.repo.walk_directories_path(recursive=True)), ['same', 'same/deep', 'same/deep/dir'])
        self.assertEqual(audit_repository(self.temporary.path), {})


class TestInfoReadsUnderUpdates(unittest.TestCase):
    """
    Reading the info of a file while it is being updated.
    """

    def test_info_is_never_read_torn(self):
        """A reader of file info never sees a half written info file."""
        with TemporaryRepository() as temporary:
            repo = temporary.repo
            repo.dump_file({'v': 0}, 'target', description='d' * 5000)
            stop    = threading.Event()
            unreadable = []

            def writer():
                counter = 0
                while not stop.is_set():
                    counter += 1
                    repo.update_file({'v': counter}, 'target', description='d' * 5000, raiseError=False)

            def reader():
                while not stop.is_set():
                    info, message = repo.get_file_info('target')
                    if info is None:
                        unreadable.append(message)

            threads = [threading.Thread(target=writer) for _ in range(2)] + [threading.Thread(target=reader) for _ in range(3)]
            for thread in threads:
                thread.start()
            time.sleep(3)
            stop.set()
            for thread in threads:
                thread.join()
            self.assertEqual(unreadable, [], describe(unreadable))


if __name__ == '__main__':
    unittest.main()
