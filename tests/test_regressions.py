"""
Regression tests, one for each bug that was found and fixed. A bug that is found and not fixed yet goes here with a
@known_bug marker, which reports it as an expected failure and announces when it gets fixed.
"""
import os
import unittest

from pyrep import Repository

from helpers import TemporaryRepository


class TestRegressions(unittest.TestCase):
    """
    Behaviour that once was broken and must stay fixed.
    """

    def setUp(self):
        self.temporary = TemporaryRepository(timeout=1)
        self.temporary.__enter__()
        self.addCleanup(self.temporary.__exit__, None, None, None)
        self.repo = self.temporary.repo

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

    def test_dill_function_is_usable_after_pull(self):
        """A function stored with dill can be called after it is pulled."""
        self.repo.dump_file(lambda value: value + 1, 'function', dump='dill')
        self.assertEqual(self.repo.pull_file('function')(1), 2)

    def test_pyrep_temporary_names_are_reserved(self):
        """Names that pyrep uses for its temporary files cannot hold user data."""
        self.assertFalse(self.repo.is_name_allowed('.pyreptmp_anything')[0])
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


if __name__ == '__main__':
    unittest.main()
