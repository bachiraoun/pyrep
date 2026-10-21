"""
Tests of rename_directory and copy_directory: argument checks, refusals, failures of locks and of the index, and failed copies.
"""
import os
import unittest

from pyrep import Repository

from helpers import TemporaryRepository, audit_repository, describe


class DirectoryTestCase(unittest.TestCase):
    """
    Base of the directory tests, a repository with a few tracked directories and helpers to make operations fail.
    """

    def setUp(self):
        """
        Creates a temporary repository for every test, it is removed afterwards.
        """
        self.temporary = TemporaryRepository(timeout=0.1)
        self.temporary.__enter__()
        self.addCleanup(self.temporary.__exit__, None, None, None)
        self.repo = self.temporary.repo
        self.repo.dump_file('one', 'a/b/file')
        self.repo.dump_file('two', 'a/other')
        self.repo.add_directory('c')

    def hold_lock(self, path):
        """
        Takes a lock of the repository locker and keeps it until the end of the test, so that the operation under test
        cannot get it.

        :Parameters:
            #. path (str): The path whose lock is taken.

        :Returns:
            #. release (callable): Releases the lock before the end of the test.
        """
        acquired, lockId = self.repo.locker.acquire_lock(path=path, timeout=1)
        self.assertTrue(acquired)
        released = []

        def release():
            if not len(released):
                released.append(self.repo.locker.release_lock(lockId))

        self.addCleanup(release)
        return release

    def assert_consistent(self):
        """
        Fails when the repository on disk has any inconsistency.
        """
        problems = audit_repository(self.temporary.path)
        self.assertEqual(problems, {}, describe(problems))

    def corrupt_index(self):
        """
        Replaces the saved index by garbage and returns the original bytes, so a test can put it back.

        :Returns:
            #. indexPath (str): The path of the index file.
            #. original (bytes): The content of the index before it was replaced.
        """
        indexPath = os.path.join(self.temporary.path, '.pyreprepo')
        with open(indexPath, 'rb') as fd:
            original = fd.read()
        with open(indexPath, 'wb') as fd:
            fd.write(b'garbage that is not a pickle')
        self.addCleanup(self.restore_index, indexPath, original)
        return indexPath, original

    @staticmethod
    def restore_index(indexPath, original):
        """
        Puts the original index bytes back.

        :Parameters:
            #. indexPath (str): The path of the index file.
            #. original (bytes): The content to write back.
        """
        with open(indexPath, 'wb') as fd:
            fd.write(original)


class TestRenameDirectory(DirectoryTestCase):
    """
    Everything rename_directory can refuse or fail on, and that it leaves the repository usable afterwards.
    """

    def test_arguments_are_checked(self):
        """Wrong argument types and values are refused before anything happens."""
        for arguments in ({'raiseError': 'yes'}, {'ntrials': 'three'}, {'ntrials': 0}):
            with self.assertRaises(Exception):
                self.repo.rename_directory('c', 'd', **arguments)
        self.assertTrue(self.repo.is_repository_directory('c'))

    def test_main_directory_cannot_be_renamed(self):
        """The repository directory itself is refused, as an error or as a failure."""
        with self.assertRaises(Exception):
            self.repo.rename_directory('', 'x')
        succeeded, message = self.repo.rename_directory('', 'x', raiseError=False)
        self.assertFalse(succeeded)
        self.assertIn('main repository directory', message)

    def test_a_bad_new_name_raises_when_asked(self):
        """A new name that is a path raises with raiseError and returns a failure without it."""
        with self.assertRaises(Exception) as caught:
            self.repo.rename_directory('c', 'x/y')
        self.assertIn('single name', str(caught.exception))
        self.assertFalse(self.repo.rename_directory('c', 'x/y', raiseError=False)[0])
        self.assertFalse(self.repo.rename_directory('c', '.pyreprepo', raiseError=False)[0])

    def test_an_existing_name_is_refused(self):
        """Renaming onto a directory that exists changes nothing."""
        self.repo.add_directory('d')
        with self.assertRaises(Exception):
            self.repo.rename_directory('c', 'd')
        succeeded, message = self.repo.rename_directory('c', 'd', raiseError=False)
        self.assertFalse(succeeded)
        self.assertIn('already exist', message)
        self.assertTrue(self.repo.is_repository_directory('c'))
        self.assert_consistent()

    def test_an_untracked_directory_fails_and_releases_its_locks(self):
        """A directory that is not tracked cannot be renamed, and the repository stays usable."""
        succeeded, message = self.repo.rename_directory('ghost', 'x', raiseError=False)
        self.assertFalse(succeeded)
        self.assertIn('ghost', message)
        with self.assertRaises(Exception):
            self.repo.rename_directory('ghost', 'x')
        self.assertTrue(self.repo.dump_file('v', 'a/later', raiseError=False)[0])

    def test_a_held_parent_lock_makes_it_fail_and_it_works_afterwards(self):
        """When the lock of the parent directory is taken, renaming fails clearly and works once it is free."""
        release = self.hold_lock(os.path.join(self.temporary.path, 'a'))
        succeeded, message = self.repo.rename_directory('a/b', 'renamed', raiseError=False)
        self.assertFalse(succeeded)
        self.assertIn('parent directory lock', message)
        release()
        self.assertTrue(self.repo.rename_directory('a/b', 'renamed')[0])
        self.assertEqual(self.repo.pull_file('a/renamed/file'), 'one')

    def test_a_held_repository_lock_makes_it_fail_and_frees_the_parent_lock(self):
        """When the repository lock is taken, renaming fails clearly and the parent lock it already took is given back."""
        release = self.hold_lock(self.temporary.path)
        succeeded, message = self.repo.rename_directory('a/b', 'renamed', raiseError=False)
        self.assertFalse(succeeded)
        self.assertIn('repository lock', message)
        with self.assertRaises(Exception):
            self.repo.rename_directory('a/b', 'renamed')
        # The parent lock was released if somebody else can take it right away
        acquired, lockId = self.repo.locker.acquire_lock(path=os.path.join(self.temporary.path, 'a'), timeout=1)
        self.assertTrue(acquired)
        self.repo.locker.release_lock(lockId)
        release()
        self.assertTrue(self.repo.rename_directory('a/b', 'renamed')[0])

    def test_a_corrupt_index_fails_cleanly_and_releases_the_locks(self):
        """An index that cannot be read fails the rename, returns the locks, and the repository works once it is back."""
        indexPath, original = self.corrupt_index()
        succeeded, message = self.repo.rename_directory('a/b', 'renamed', raiseError=False)
        self.assertFalse(succeeded)
        self.assertIn('load', message.lower())
        with self.assertRaises(Exception):
            self.repo.rename_directory('a/b', 'renamed')
        self.restore_index(indexPath, original)
        self.assertTrue(self.repo.rename_directory('a/b', 'renamed')[0])
        self.assert_consistent()

    def test_renaming_keeps_everything_inside(self):
        """Files and directories below a renamed directory are all reachable under the new name."""
        self.repo.dump_file('deep', 'a/b/deeper/file')
        self.assertEqual(self.repo.rename_directory('a', 'z'), (True, None))
        reloaded = Repository(self.temporary.path, timeout=1)
        self.addCleanup(reloaded.close)
        self.assertEqual(sorted(reloaded.walk_files_path(recursive=True)), ['z/b/deeper/file', 'z/b/file', 'z/other'])
        self.assertEqual(reloaded.pull_file('z/b/deeper/file'), 'deep')
        self.assert_consistent()


class TestCopyDirectory(DirectoryTestCase):
    """
    Everything copy_directory can refuse or fail on, and what a failed copy leaves behind.
    """

    def test_arguments_are_checked(self):
        """Wrong argument types and values are refused before anything happens."""
        for arguments in ({'raiseError': 'yes'}, {'overwrite': 'yes'}, {'ntrials': 'three'}, {'ntrials': 0}):
            with self.assertRaises(Exception):
                self.repo.copy_directory('a', 'copy', **arguments)
        self.assertFalse(self.repo.is_repository_directory('copy'))

    def test_the_refusals(self):
        """The main directory, an untracked source, the same path and a tracked destination are all refused."""
        cases = [('', 'copy', 'main directory'), ('ghost', 'copy', 'not a tracked'), ('a', 'a', 'same directory'), ('a', 'c', 'tracked repository directory')]
        for source, destination, expected in cases:
            with self.assertRaises(Exception):
                self.repo.copy_directory(source, destination)
            succeeded, message = self.repo.copy_directory(source, destination, raiseError=False)
            self.assertFalse(succeeded, source)
            self.assertIn(expected, message, source)
        self.assert_consistent()

    def test_an_untracked_directory_on_disk_needs_overwrite(self):
        """A directory that exists on disk but is not tracked is kept, unless overwrite is given and it is replaced."""
        stray = os.path.join(self.temporary.path, 'copy')
        os.mkdir(stray)
        with open(os.path.join(stray, 'stray.txt'), 'w') as fd:
            fd.write('not tracked')
        with self.assertRaises(Exception):
            self.repo.copy_directory('a', 'copy')
        succeeded, message = self.repo.copy_directory('a', 'copy', raiseError=False)
        self.assertFalse(succeeded)
        self.assertIn('overwrite', message)
        self.assertTrue(os.path.isfile(os.path.join(stray, 'stray.txt')))
        self.assertEqual(self.repo.copy_directory('a', 'copy', overwrite=True), (True, None))
        self.assertFalse(os.path.exists(os.path.join(stray, 'stray.txt')))
        self.assertEqual(self.repo.pull_file('copy/b/file'), 'one')
        self.assert_consistent()

    def test_a_destination_below_a_file_fails_without_leaving_anything(self):
        """A destination whose parent is a file cannot be created and nothing is tracked or left on disk."""
        self.repo.dump_file('plain', 'plain')
        succeeded, message = self.repo.copy_directory('a', 'plain/inside', raiseError=False)
        self.assertFalse(succeeded)
        with self.assertRaises(Exception):
            self.repo.copy_directory('a', 'plain/inside')
        self.assertFalse(self.repo.is_repository_directory('plain/inside'))
        self.assertFalse(os.path.exists(os.path.join(self.temporary.path, 'plain', 'inside')))
        self.assert_consistent()

    def test_a_held_repository_lock_makes_it_fail(self):
        """When the repository lock is taken, copying fails clearly and works once it is free."""
        release = self.hold_lock(self.temporary.path)
        succeeded, message = self.repo.copy_directory('a/b', 'c/copy', raiseError=False)
        self.assertFalse(succeeded)
        self.assertIn('lock', message)
        with self.assertRaises(Exception):
            self.repo.copy_directory('a/b', 'c/copy')
        release()
        self.assertTrue(self.repo.copy_directory('a/b', 'c/copy')[0])

    def test_a_held_source_parent_lock_makes_it_fail(self):
        """When the lock of the source's parent directory is taken, copying fails and the repository lock is given back."""
        release = self.hold_lock(os.path.join(self.temporary.path, 'a'))
        succeeded, message = self.repo.copy_directory('a/b', 'c/copy', raiseError=False)
        self.assertFalse(succeeded)
        self.assertIn('lock', message)
        acquired, lockId = self.repo.locker.acquire_lock(path=self.temporary.path, timeout=1)
        self.assertTrue(acquired)
        self.repo.locker.release_lock(lockId)
        release()
        self.assertTrue(self.repo.copy_directory('a/b', 'c/copy')[0])

    def test_a_held_destination_parent_lock_makes_it_fail(self):
        """When the lock of the destination's parent directory is taken, copying fails and both other locks are given back."""
        release = self.hold_lock(os.path.join(self.temporary.path, 'c'))
        succeeded, message = self.repo.copy_directory('a/b', 'c/copy', raiseError=False)
        self.assertFalse(succeeded)
        self.assertIn('lock', message)
        for path in (self.temporary.path, os.path.join(self.temporary.path, 'a')):
            acquired, lockId = self.repo.locker.acquire_lock(path=path, timeout=1)
            self.assertTrue(acquired, path)
            self.repo.locker.release_lock(lockId)
        release()
        self.assertTrue(self.repo.copy_directory('a/b', 'c/copy')[0])

    def test_a_corrupt_index_fails_cleanly(self):
        """An index that cannot be read fails the copy and the repository works once it is back."""
        indexPath, original = self.corrupt_index()
        succeeded, message = self.repo.copy_directory('a/b', 'c/copy', raiseError=False)
        self.assertFalse(succeeded)
        with self.assertRaises(Exception):
            self.repo.copy_directory('a/b', 'c/copy')
        self.restore_index(indexPath, original)
        self.assertTrue(self.repo.copy_directory('a/b', 'c/copy')[0])

    def test_a_copy_that_fails_halfway_is_reported_and_the_source_survives(self):
        """When a tracked file is missing on disk the copy fails after its trials, the source stays whole and the copy is not tracked."""
        os.remove(os.path.join(self.temporary.path, 'a', 'b', 'file'))
        succeeded, message = self.repo.copy_directory('a/b', 'c/copy', raiseError=False)
        self.assertFalse(succeeded)
        self.assertIn('No such file', message)
        with self.assertRaises(Exception) as caught:
            self.repo.copy_directory('a/b', 'c/copy2')
        self.assertIn('Unable to copy directory', str(caught.exception))
        self.assertFalse(self.repo.is_repository_directory('c/copy'))
        self.assertTrue(self.repo.is_repository_directory('a/b'))
        self.assertEqual(self.repo.pull_file('a/other'), 'two')

    def test_a_copy_is_independent_of_its_source(self):
        """Changing a file of the copy does not change the source, and removing the source keeps the copy."""
        self.assertEqual(self.repo.copy_directory('a', 'c/copy'), (True, None))
        self.repo.update_file('changed', 'c/copy/other')
        self.assertEqual(self.repo.pull_file('a/other'), 'two')
        self.repo.remove_directory('a')
        self.assertEqual(self.repo.pull_file('c/copy/b/file'), 'one')
        self.assert_consistent()


if __name__ == '__main__':
    unittest.main()
