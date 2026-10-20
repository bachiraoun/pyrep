"""
Tests of the guards that keep operations inside the repository and protect data from accidental loss.
"""
import os
import sys
import pickle
import warnings
import unittest
import subprocess

from pyrep import Repository

from helpers import TemporaryRepository


class TestPathGuards(unittest.TestCase):
    """
    Relative paths must never lead outside of the repository directory.
    """

    def setUp(self):
        self.temporary = TemporaryRepository(timeout=5)
        self.temporary.__enter__()
        self.addCleanup(self.temporary.__exit__, None, None, None)
        self.repo    = self.temporary.repo
        self.outside = os.path.join(self.temporary.root, 'outside')
        os.mkdir(self.outside)

    def assert_outside_untouched(self):
        """
        Fails when anything was created next to the repository.
        """
        self.assertEqual(os.listdir(self.outside), [])
        self.assertEqual(sorted(os.listdir(self.temporary.root)), ['outside', 'repo'])

    def test_parent_components_are_rejected(self):
        """Paths that climb out with '..' raise for every operation."""
        self.repo.dump_file('v', 'inside')
        attempts = [lambda: self.repo.dump_file('x', '../escape'),
                    lambda: self.repo.dump_file('x', 'a/../../escape', raiseError=False),
                    lambda: self.repo.add_directory('../dir'),
                    lambda: self.repo.copy_file('inside', '../copy'),
                    lambda: self.repo.rename_file('inside', '../moved'),
                    lambda: self.repo.pull_file('../inside')]
        for attempt in attempts:
            with self.assertRaises(Exception):
                attempt()
        self.assert_outside_untouched()
        self.assertEqual(self.repo.pull_file('inside'), 'v')

    def test_dots_that_stay_inside_are_accepted(self):
        """A path that goes down and back up is normalised and works."""
        self.assertTrue(self.repo.dump_file('v', 'a/../b')[0])
        self.assertEqual(self.repo.pull_file('b'), 'v')

    def test_absolute_paths_outside_stay_inside(self):
        """An absolute path is interpreted relative to the repository."""
        self.assertTrue(self.repo.dump_file('v', os.path.join(self.outside, 'file'))[0])
        self.assert_outside_untouched()

    @unittest.skipIf(sys.platform.startswith('win'), 'symbolic links need privileges on Windows')
    def test_symlink_leading_outside_is_rejected(self):
        """A symbolic link inside the repository cannot be used to write outside."""
        os.symlink(self.outside, os.path.join(self.temporary.path, 'evil'))
        with self.assertRaises(Exception):
            self.repo.dump_file('x', 'evil/file')
        with self.assertRaises(Exception):
            self.repo.add_directory('evil/sub')
        self.assertEqual(os.listdir(self.outside), [])

    @unittest.skipIf(sys.platform.startswith('win'), 'symbolic links need privileges on Windows')
    def test_symlink_staying_inside_is_accepted(self):
        """A symbolic link to another directory of the same repository works."""
        self.repo.add_directory('real')
        os.symlink(os.path.join(self.temporary.path, 'real'), os.path.join(self.temporary.path, 'alias'))
        self.assertTrue(self.repo.dump_file('v', 'alias/file')[0])

    def test_reserved_names_are_rejected(self):
        """Internal file names cannot be used for user data."""
        for name in ('.pyreprepo', '.pyreplock', '.pyrepdirinfo', '.pyrepdirlock', 'sub/.pyreprepo'):
            self.assertFalse(self.repo.is_name_allowed(name)[0], name)
            self.assertFalse(self.repo.dump_file('x', name, raiseError=False)[0], name)
        for name in ('.x_pyrepfileinfo', '.x_pyrepfilelock'):
            self.assertFalse(self.repo.is_name_allowed(name)[0], name)


class TestDataLossGuards(unittest.TestCase):
    """
    Operations that can erase data must be explicit.
    """

    def test_replace_erases_untracked_files_only_when_asked(self):
        """create_repository keeps stray files unless replace=True."""
        with TemporaryRepository() as temporary:
            stray = os.path.join(temporary.path, 'stray.txt')
            with open(stray, 'w') as fd:
                fd.write('keep me')
            self.assertFalse(temporary.repo.create_repository(temporary.path, raiseError=False)[0])
            self.assertTrue(os.path.isfile(stray))
            self.assertTrue(temporary.repo.create_repository(temporary.path, replace=True)[0])
            self.assertFalse(os.path.isfile(stray))

    def test_failed_create_keeps_previous_repository(self):
        """A create that fails leaves the instance on its previous repository."""
        if hasattr(os, 'geteuid') and os.geteuid() == 0:
            self.skipTest('root can write into read-only directories')
        with TemporaryRepository(timeout=3) as temporary:
            temporary.repo.dump_file('keep', 'f')
            readOnly = os.path.join(temporary.root, 'readonly')
            os.mkdir(readOnly)
            os.chmod(readOnly, 0o555)
            try:
                self.assertFalse(temporary.repo.create_repository(readOnly, raiseError=False)[0])
                self.assertEqual(temporary.repo.path, temporary.path)
                self.assertEqual(temporary.repo.pull_file('f'), 'keep')
                self.assertTrue(temporary.repo.dump_file('after', 'g')[0])
            finally:
                # The directory must be writable again or the temporary directory cannot be removed
                os.chmod(readOnly, 0o755)

    def test_custom_password_is_not_pickled(self):
        """A password given by the user never reaches a pickle."""
        with TemporaryRepository(password='a-very-secret-value') as temporary:
            blob = pickle.dumps(temporary.repo)
            self.assertNotIn(b'a-very-secret-value', blob)
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always')
                clone = pickle.loads(blob)
            self.assertIsNone(clone.path)
            self.assertTrue(any('password' in str(item.message) for item in caught))

    def test_errors_still_raise_with_asserts_disabled(self):
        """raiseError keeps working under python -O, where assert statements vanish."""
        code = ("import sys, tempfile, os\n"
                "from pyrep import Repository\n"
                "root = tempfile.mkdtemp()\n"
                "repo = Repository(timeout=5)\n"
                "repo.create_repository(os.path.join(root, 'r'))\n"
                "try:\n"
                "    repo.remove_file('ghost')\n"
                "    print('NO-ERROR')\n"
                "except Exception:\n"
                "    print('RAISED')\n"
                "print(repo.remove_file('ghost', raiseError=False)[0])\n"
                "repo.close()\n")
        output = subprocess.check_output([sys.executable, '-O', '-c', code], universal_newlines=True)
        self.assertEqual(output.split(), ['RAISED', 'False'])

    def test_existing_file_is_protected_with_asserts_disabled(self):
        """Under python -O a second dump without replace still refuses to overwrite."""
        code = ("import tempfile, os\n"
                "from pyrep import Repository\n"
                "repo = Repository(timeout=5)\n"
                "repo.create_repository(os.path.join(tempfile.mkdtemp(), 'r'))\n"
                "repo.dump_file('first', 'name')\n"
                "print(repo.dump_file('second', 'name', raiseError=False)[0])\n"
                "print(repo.pull_file('name'))\n"
                "repo.close()\n")
        output = subprocess.check_output([sys.executable, '-O', '-c', code], universal_newlines=True)
        self.assertEqual(output.split(), ['False', 'first'])


if __name__ == '__main__':
    unittest.main()
