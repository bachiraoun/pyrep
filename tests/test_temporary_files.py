"""
Tests of the temporary files that crashed writes leave behind, and of their removal when a repository is loaded.
"""
import os
import time
import warnings
import unittest
from unittest import mock

from pyrep import Repository

from helpers import TemporaryRepository, audit_repository


def make_leftover(directory, name, age):
    """
    Creates a temporary file that looks like the leftover of a crashed write.

    :Parameters:
        #. directory (str): The directory to create it in.
        #. name (str): The file name.
        #. age (int, float): How many seconds ago the file was last modified.

    :Returns:
        #. path (str): The path of the file.
    """
    path = os.path.join(directory, name)
    with open(path, 'wb') as fd:
        fd.write(b'half written')
    past = time.time() - age
    os.utime(path, (past, past))
    return path


class TestTemporaryFilesAtLoad(unittest.TestCase):
    """
    Loading a repository removes old leftovers and nothing else.
    """

    def setUp(self):
        """
        Creates a temporary repository for every test, it is removed afterwards.
        """
        self.temporary = TemporaryRepository(timeout=3)
        self.temporary.__enter__()
        self.addCleanup(self.temporary.__exit__, None, None, None)
        self.repo = self.temporary.repo
        self.repo.dump_file('v', 'tracked/file')
        self.root      = self.temporary.path
        self.tracked   = os.path.join(self.root, 'tracked')
        self.untracked = os.path.join(self.root, 'created_by_a_crashed_add_directory')
        os.mkdir(self.untracked)
        self.old    = [make_leftover(self.root, '.pyreptmp_11_aaaaaaaa_.pyreprepo', 7200),
                       make_leftover(self.tracked, '.pyreptmp_12_bbbbbbbb_file', 7200),
                       make_leftover(self.untracked, '.pyreptmp_13_cccccccc_.pyrepdirinfo', 7200)]
        self.recent = make_leftover(self.tracked, '.pyreptmp_14_dddddddd_file', 5)

    def load(self, **arguments):
        """
        Loads the repository in a new instance.

        :Parameters:
            #. arguments (dict): Keyword arguments of load_repository, and attributes to set on the instance first under the key attributes.

        :Returns:
            #. repo (pyrep.Repository): The instance that loaded the repository.
        """
        repo = Repository(timeout=3)
        for name, value in arguments.pop('attributes', {}).items():
            setattr(repo, name, value)
        repo.load_repository(self.root, **arguments)
        self.addCleanup(repo.close)
        return repo

    def test_loading_removes_old_leftovers_everywhere_and_spares_recent_ones(self):
        """Old temporary files go, in the repository directory, in tracked directories and in untracked ones. A recent one stays."""
        self.load()
        self.assertEqual([path for path in self.old if os.path.exists(path)], [])
        self.assertTrue(os.path.exists(self.recent))

    def test_the_constructor_cleans_by_default(self):
        """Creating a Repository with a path loads it and cleans like load_repository."""
        repo = Repository(self.root, timeout=3)
        self.addCleanup(repo.close)
        self.assertEqual([path for path in self.old if os.path.exists(path)], [])

    def test_the_flag_turns_cleaning_off(self):
        """With the flag off nothing is removed, by load_repository or by the constructor."""
        self.load(removeTemporaryFiles=False)
        repo = Repository(self.root, timeout=3, removeTemporaryFiles=False)
        self.addCleanup(repo.close)
        self.assertEqual([path for path in self.old if os.path.exists(path)], self.old)

    def test_the_age_limit_can_be_changed(self):
        """A shorter limit also removes the recent leftover once it is older than the limit."""
        make_leftover(self.tracked, '.pyreptmp_15_eeeeeeee_file', 60)
        self.load(attributes={'TEMPORARY_FILES_MAX_AGE': 30})
        remaining = sorted(name for name in os.listdir(self.tracked) if name.startswith('.pyreptmp_'))
        self.assertEqual(remaining, ['.pyreptmp_14_dddddddd_file'])

    def test_a_failing_cleanup_only_warns(self):
        """When removing the leftovers fails the repository still loads and a warning says why."""
        with mock.patch.object(Repository, 'remove_temporary_files', side_effect=OSError('disk on fire')):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always')
                repo = self.load()
        self.assertEqual(repo.pull_file('tracked/file'), 'v')
        self.assertTrue(any('temporary files' in str(item.message) and 'disk on fire' in str(item.message) for item in caught))
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            with mock.patch.object(Repository, 'remove_temporary_files', side_effect=OSError('disk on fire')):
                self.load(verbose=False)
        self.assertFalse(any('temporary files' in str(item.message) for item in caught))

    def test_cleaning_never_touches_repository_data(self):
        """Tracked files, info files and the index survive a cleaning load untouched."""
        self.load()
        self.assertEqual(audit_repository(self.root), {})
        self.assertEqual(self.repo.pull_file('tracked/file'), 'v')

    def test_a_manual_call_cleans_with_its_own_age(self):
        """remove_temporary_files can be called at any time with any age."""
        removed = self.repo.remove_temporary_files(olderThan=1)
        self.assertEqual(sorted(removed), sorted(os.path.relpath(path, self.root) for path in self.old + [self.recent]))


if __name__ == '__main__':
    unittest.main()
