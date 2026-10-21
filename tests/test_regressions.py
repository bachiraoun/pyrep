"""
Regression tests, one for each bug that was found and fixed. A bug that is found and not fixed yet goes here with a
@known_bug marker, which reports it as an expected failure and announces when it gets fixed.
"""
import os
import time
import unittest
import importlib.util

from pyrep import Repository

from helpers import TemporaryRepository


class TestRegressions(unittest.TestCase):
    """
    Behaviour that once was broken and must stay fixed.
    """

    def setUp(self):
        """
        Creates a temporary repository for every test, it is removed afterwards.
        """
        self.temporary = TemporaryRepository(timeout=1)
        self.temporary.__enter__()
        self.addCleanup(self.temporary.__exit__, None, None, None)
        self.repo = self.temporary.repo

    @unittest.skipUnless(importlib.util.find_spec('dill'), 'dill is not installed')
    def test_dill_stores_a_function(self):
        """The dill keyword stores a function, which is what dill is for."""
        self.assertTrue(self.repo.dump_file(lambda value: value + 1, 'function', dump='dill', raiseError=False)[0])

    def test_remove_repository_removes_the_directory(self):
        """After remove_repository with removeEmptyDirs nothing of the repository directory is left."""
        with TemporaryRepository() as other:
            other.repo.dump_file('v', 'sub/tracked')
            other.repo.remove_repository(removeEmptyDirs=True)
            self.assertFalse(os.path.exists(other.path))

    def test_json_keyword_roundtrip(self):
        """Dumping with the json keyword works."""
        self.assertTrue(self.repo.dump_file({'a': 1}, 'j', dump='json', raiseError=False)[0])
        self.assertEqual(self.repo.pull_file('j'), {'a': 1})

    def test_update_with_keywords_for_everything(self):
        """update_file accepts method keywords when every argument is given."""
        self.repo.dump_file(1, 'u')
        succeeded, message = self.repo.update_file({'a': 2}, 'u', description='', dump='pickle', pull='pickle', raiseError=False)
        self.assertTrue(succeeded, message)

    def test_remove_top_level_directory(self):
        """A top level directory can be removed and the repository stays usable."""
        self.repo.add_directory('top')
        self.assertTrue(self.repo.remove_directory('top', raiseError=False)[0])
        self.assertTrue(self.repo.dump_file('v', 'after', raiseError=False)[0])

    def test_remove_directory_keeps_each_sibling_once(self):
        """Removing a directory leaves its sibling files untouched."""
        self.repo.add_directory('p/gone')
        self.repo.dump_file('v', 'p/keepme')
        self.assertTrue(self.repo.remove_directory('p/gone', raiseError=False)[0])
        self.assertEqual(list(self.repo.walk_files_path('p')), ['p/keepme'])

    def test_rename_directory_rejects_path_in_new_name(self):
        """A new directory name that climbs out of the repository is refused."""
        self.repo.dump_file('v', 'src/file')
        outsideDirectory = os.path.join(self.temporary.root, 'escaped')
        try:
            self.repo.rename_directory('src', '../escaped', raiseError=False)
            self.assertFalse(os.path.exists(outsideDirectory))
        finally:
            if os.path.isdir(outsideDirectory):
                os.rename(outsideDirectory, outsideDirectory + '_leftover')

    def test_class_file_pattern_is_reserved(self):
        """Names that look like pyrep class files are reserved."""
        self.assertFalse(self.repo.is_name_allowed('.x_pyrepfileclass')[0])

    def test_other_instance_sees_new_files_after_refresh(self):
        """An instance sees what another instance dumped once it refreshes, and not before."""
        other = Repository(self.temporary.path, timeout=1)
        self.addCleanup(other.close)
        self.repo.dump_file('from-first', 'shared_name')
        self.assertEqual(list(other.walk_files_path()), [])
        self.assertTrue(other.refresh_repository()[0])
        self.assertEqual(other.pull_file('shared_name'), 'from-first')

    def test_closing_one_instance_keeps_the_others_working(self):
        """Closing an instance leaves other instances of the same repository usable."""
        sibling = Repository(self.temporary.path, timeout=1)
        sibling.close()
        self.assertTrue(self.repo.dump_file('v', 'after_close', raiseError=False)[0])

    def test_json_keyword_in_update(self):
        """update_file converts the json keyword too."""
        self.repo.dump_file({'a': 1}, 'j', dump='json')
        self.assertTrue(self.repo.update_file({'a': 2}, 'j', description='', dump='json', pull='json', raiseError=False)[0])
        self.assertEqual(self.repo.pull_file('j'), {'a': 2})

    @unittest.skipUnless(importlib.util.find_spec('dill'), 'dill is not installed')
    def test_dill_function_is_usable_after_pull(self):
        """A function stored with dill can be called after it is pulled."""
        self.repo.dump_file(lambda value: value + 1, 'function', dump='dill')
        self.assertEqual(self.repo.pull_file('function')(1), 2)

    def test_pyrep_temporary_names_are_reserved(self):
        """Names that pyrep uses for its temporary files cannot hold user data."""
        self.assertFalse(self.repo.is_name_allowed('.pyreptmp_anything')[0])
        self.assertFalse(self.repo.is_name_allowed('.anything_pyrepjournal')[0])
        self.assertFalse(self.repo.is_name_allowed('.pyrepjournal')[0])
        self.assertFalse(self.repo.dump_file('v', '.pyreptmp_anything', raiseError=False)[0])

    def test_rename_directory_only_accepts_a_single_name(self):
        """A new directory name with separators or dots is refused and nothing moves."""
        self.repo.dump_file('v', 'src/file')
        for newName in ('../escaped', 'a/b', '.', '..', ''):
            self.assertFalse(self.repo.rename_directory('src', newName, raiseError=False)[0], newName)
        self.assertEqual(os.listdir(self.temporary.root), ['repo'])
        self.assertEqual(self.repo.pull_file('src/file'), 'v')

    def test_remove_top_level_directory_with_files_inside(self):
        """Removing a top level directory removes its files and keeps the others."""
        self.repo.dump_file('v', 'gone/file')
        self.repo.dump_file('v', 'stays/file')
        self.repo.dump_file('v', 'top_file')
        self.assertTrue(self.repo.remove_directory('gone', raiseError=False)[0])
        self.assertEqual(sorted(self.repo.walk_files_path(recursive=True)), ['stays/file', 'top_file'])
        self.assertTrue(self.repo.dump_file('v', 'later', raiseError=False)[0])

    def test_removing_a_top_level_directory_deletes_its_files_from_disk(self):
        """remove_directory without clean removes the tracked files of a top level directory from disk too, as for nested ones."""
        self.repo.dump_file('one', 'top/inner/file')
        self.repo.dump_file('two', 'top/other')
        self.repo.dump_file('keep', 'keepme')
        self.assertTrue(self.repo.remove_directory('top', raiseError=False)[0])
        left = sorted(os.path.relpath(os.path.join(root, name), self.temporary.path)
                      for root, _, names in os.walk(self.temporary.path) for name in names if not name.startswith('.'))
        self.assertEqual(left, ['keepme'])

    def test_the_state_of_the_empty_path_is_the_whole_repository(self):
        """Asking for the state of the repository root as an empty path gives the same as asking for everything."""
        self.repo.dump_file('v', 'a/file')
        self.assertEqual(self.repo.get_repository_state(''), self.repo.get_repository_state())
        self.assertEqual(self.repo.get_repository_state('.'), self.repo.get_repository_state())

    def test_file_methods_refuse_the_repository_directory_at_once(self):
        """Giving the repository directory where a file is needed is refused immediately, without waiting for a lock."""
        self.repo.dump_file('v', 'top')
        for root in ('', '.'):
            calls = [lambda raiseError, root=root: self.repo.remove_file(root, raiseError=raiseError),
                     lambda raiseError, root=root: self.repo.copy_file('top', root, raiseError=raiseError),
                     lambda raiseError, root=root: self.repo.rename_file('top', root, raiseError=raiseError),
                     lambda raiseError, root=root: self.repo.copy_file(root, 'other', raiseError=raiseError),
                     lambda raiseError, root=root: self.repo.rename_file(root, 'other', raiseError=raiseError)]
            for call in calls:
                start = time.time()
                succeeded, message = call(False)
                self.assertFalse(succeeded)
                self.assertIn('not a file', message)
                with self.assertRaises(Exception) as caught:
                    call(True)
                self.assertIn('not a file', str(caught.exception))
                self.assertLess(time.time() - start, 1.0)
        self.assertEqual(sorted(self.repo.walk_files_path(recursive=True)), ['top'])
        self.assertEqual(self.repo.pull_file('top'), 'v')

    def test_copying_a_directory_to_the_root_says_so(self):
        """The repository directory cannot be the destination of a directory copy, and the message says that."""
        self.repo.dump_file('v', 'a/file')
        for root in ('', '.'):
            succeeded, message = self.repo.copy_directory('a', root, raiseError=False)
            self.assertFalse(succeeded)
            self.assertIn('main directory', message)
            with self.assertRaises(Exception):
                self.repo.copy_directory('a', root)


if __name__ == '__main__':
    unittest.main()
