"""
Tests of the orphan files that crashed operations leave behind, and of their removal when a repository is loaded.
"""
import os
import time
import warnings
import unittest
import multiprocessing
from unittest import mock

from pyrep import Repository

from helpers import LOCK_TIMEOUT, TemporaryRepository, audit_repository, run_in_processes


def make_triple(directory, name, age, pieces=('data', 'info', 'class')):
    """
    Creates the files pyrep writes for a data file, with the given age.

    :Parameters:
        #. directory (str): The directory to create them in.
        #. name (str): The name of the data file.
        #. age (int, float): How many seconds ago the files were last modified.
        #. pieces (tuple): Which of the data file, the info file and the class file to create.

    :Returns:
        #. paths (list): The created paths.
    """
    names = {'data': name, 'info': '.%s_pyrepfileinfo'%name, 'class': '.%s_pyrepfileclass'%name}
    paths = []
    for piece in pieces:
        path = os.path.join(directory, names[piece])
        with open(path, 'wb') as fd:
            fd.write(b'left behind')
        past = time.time() - age
        os.utime(path, (past, past))
        paths.append(path)
    return paths


def dump_new_files(path, index, seconds, resultQueue):
    """
    Process body: dumps new files into the repository for a while.

    :Parameters:
        #. path (str): The repository path.
        #. index (int): Identity of this process.
        #. seconds (number): How long to dump.
        #. resultQueue (multiprocessing.Queue): Receives the names of the files that were dumped.
    """
    repo  = Repository(path, timeout=LOCK_TIMEOUT)
    names = []
    end   = time.time() + seconds
    while time.time() < end:
        name = 'w%i/f%i'%(index, len(names))
        if repo.dump_file({'writer': index, 'n': len(names)}, name, raiseError=False)[0]:
            names.append(name)
    resultQueue.put({'index': index, 'names': names})


def load_sweeping(path, index, seconds, resultQueue):
    """
    Process body: loads the repository again and again, removing orphan files however young they are.

    :Parameters:
        #. path (str): The repository path.
        #. index (int): Identity of this process.
        #. seconds (number): How long to keep loading.
        #. resultQueue (multiprocessing.Queue): Receives the number of loads and of failures.
    """
    loads = failures = 0
    end   = time.time() + seconds
    while time.time() < end:
        repo = Repository(timeout=LOCK_TIMEOUT)
        repo.ORPHAN_FILES_MAX_AGE = 0
        try:
            repo.load_repository(path)
            loads += 1
        except Exception:
            failures += 1
        repo.close()
    resultQueue.put({'index': index, 'loads': loads, 'failures': failures})


class TestOrphanFiles(unittest.TestCase):
    """
    What counts as an orphan, and that nothing else is touched.
    """

    def setUp(self):
        self.temporary = TemporaryRepository(timeout=0.1)
        self.temporary.__enter__()
        self.addCleanup(self.temporary.__exit__, None, None, None)
        self.repo = self.temporary.repo
        self.repo.dump_file('kept', 'tracked/file')
        self.root    = self.temporary.path
        self.tracked = os.path.join(self.root, 'tracked')

    def test_untracked_files_of_pyrep_are_removed_and_everything_else_stays(self):
        """Old files that carry pyrep's info or class file and are not tracked go. Tracked files, young orphans and files of your own stay."""
        orphans   = make_triple(self.tracked, 'orphan', 7200)
        half      = make_triple(self.tracked, 'half', 7200, pieces=('info', 'class'))
        dataless  = make_triple(self.tracked, 'infoonly', 7200, pieces=('info',))
        young     = make_triple(self.tracked, 'young', 5)
        mine      = make_triple(self.tracked, 'my_own_file', 7200, pieces=('data',))
        undirected = os.path.join(self.root, 'copy_that_was_never_registered')
        os.mkdir(undirected)
        strays    = make_triple(undirected, 'stray', 7200)
        removed   = self.repo.remove_orphan_files(olderThan=3600)
        self.assertEqual(sorted(removed), sorted(os.path.relpath(path, self.root) for path in orphans + half + dataless + strays))
        for path in orphans + half + dataless + strays:
            self.assertFalse(os.path.exists(path), path)
        for path in young + mine:
            self.assertTrue(os.path.exists(path), path)
        self.assertTrue(os.path.isdir(undirected))
        self.assertEqual(self.repo.pull_file('tracked/file'), 'kept')
        self.assertEqual(audit_repository(self.root).get('tracked-but-missing-on-disk'), None)

    def test_a_group_with_one_recent_file_is_left_whole(self):
        """The files of one orphan are removed together or not at all, by the age of the youngest."""
        old   = make_triple(self.tracked, 'mixed', 7200, pieces=('data', 'info'))
        young = make_triple(self.tracked, 'mixed', 5, pieces=('class',))
        self.assertEqual(self.repo.remove_orphan_files(olderThan=3600), [])
        for path in old + young:
            self.assertTrue(os.path.exists(path), path)
        self.assertEqual(len(self.repo.remove_orphan_files(olderThan=1)), 3)

    def test_the_age_must_be_a_number(self):
        """A wrong age is refused."""
        for age in (-1, 'a', None):
            with self.assertRaises(Exception):
                self.repo.remove_orphan_files(olderThan=age)

    def test_nothing_to_remove_needs_no_lock(self):
        """With no orphan the call returns at once, even while another process holds the repository lock."""
        acquired, lockId = self.repo.locker.acquire_lock(path=self.root, timeout=1)
        self.assertTrue(acquired)
        self.addCleanup(self.repo.locker.release_lock, lockId)
        start = time.time()
        self.assertEqual(self.repo.remove_orphan_files(), [])
        self.assertLess(time.time() - start, 1.0)
        make_triple(self.tracked, 'orphan', 7200)
        with self.assertRaises(Exception) as caught:
            self.repo.remove_orphan_files()
        self.assertIn('repository lock', str(caught.exception))


class TestOrphanFilesAtLoad(unittest.TestCase):
    """
    Loading a repository removes orphans, unless it is told not to.
    """

    def setUp(self):
        self.temporary = TemporaryRepository(timeout=3)
        self.temporary.__enter__()
        self.addCleanup(self.temporary.__exit__, None, None, None)
        self.temporary.repo.dump_file('kept', 'tracked/file')
        self.orphans = make_triple(os.path.join(self.temporary.path, 'tracked'), 'orphan', 7200)

    def left(self):
        """
        The orphan files that are still there.
        """
        return [path for path in self.orphans if os.path.exists(path)]

    def test_loading_removes_old_orphans_by_default(self):
        """load_repository and the constructor both remove them."""
        repo = Repository(self.temporary.path, timeout=3)
        self.addCleanup(repo.close)
        self.assertEqual(self.left(), [])
        self.assertEqual(repo.pull_file('tracked/file'), 'kept')

    def test_the_flag_turns_it_off(self):
        """With the flag off nothing is removed, by load_repository or by the constructor."""
        repo = Repository(self.temporary.path, timeout=3, removeOrphanFiles=False)
        self.addCleanup(repo.close)
        other = Repository(timeout=3)
        other.load_repository(self.temporary.path, removeOrphanFiles=False)
        self.addCleanup(other.close)
        self.assertEqual(self.left(), self.orphans)

    def test_young_orphans_wait_for_their_age(self):
        """A recent orphan stays until it is old enough, and the limit can be changed."""
        young = make_triple(os.path.join(self.temporary.path, 'tracked'), 'young', 120)
        repo = Repository(timeout=3)
        repo.load_repository(self.temporary.path)
        self.addCleanup(repo.close)
        self.assertTrue(all(os.path.exists(path) for path in young))
        other = Repository(timeout=3)
        other.ORPHAN_FILES_MAX_AGE = 60
        other.load_repository(self.temporary.path)
        self.addCleanup(other.close)
        self.assertFalse(any(os.path.exists(path) for path in young))

    def test_a_failing_sweep_only_warns(self):
        """When the sweep fails the repository still loads and a warning says why."""
        with mock.patch.object(Repository, 'remove_orphan_files', side_effect=OSError('disk on fire')):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always')
                repo = Repository(self.temporary.path, timeout=3)
        self.addCleanup(repo.close)
        self.assertEqual(repo.pull_file('tracked/file'), 'kept')
        self.assertTrue(any('orphan files' in str(item.message) and 'disk on fire' in str(item.message) for item in caught))


class TestOrphanSweepAgainstWriters(unittest.TestCase):
    """
    Sweeping while others write must never remove a file that is, or is about to be, tracked.
    """

    def test_loading_with_a_sweep_never_removes_files_being_dumped(self):
        """Three processes dump new files while two keep loading and sweeping with no age limit, and every dumped file is still tracked and readable."""
        with TemporaryRepository(timeout=60) as temporary:
            context = multiprocessing.get_context('spawn')
            queue   = context.Queue()
            processes = [context.Process(target=dump_new_files, args=(temporary.path, index, 6, queue)) for index in range(3)]
            processes += [context.Process(target=load_sweeping, args=(temporary.path, 10 + index, 6, queue)) for index in range(2)]
            for process in processes:
                process.start()
            results = [queue.get(timeout=120) for _ in processes]
            for process in processes:
                process.join(30)
            names = [name for result in results if 'names' in result for name in result['names']]
            self.assertGreater(len(names), 20)
            self.assertEqual(sum(result['failures'] for result in results if 'failures' in result), 0)
            fresh = Repository(temporary.path, timeout=60)
            self.addCleanup(fresh.close)
            self.assertEqual(sorted(fresh.walk_files_path(recursive=True)), sorted(names))
            for name in names[::7]:
                self.assertIsInstance(fresh.pull_file(name), dict)
            self.assertEqual(audit_repository(temporary.path), {})


if __name__ == '__main__':
    unittest.main()
