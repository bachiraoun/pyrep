"""
Functional tests of every public pyrep operation, checked through a fresh instance that reloads the repository from disk.
"""
import os
import tarfile
import warnings
import unittest
import importlib.util

from pyrep import Repository

from helpers import TemporaryRepository, audit_repository, describe, read_index


class TestBasicOperations(unittest.TestCase):
    """
    Single process, single thread behaviour of files, directories and metadata.
    """

    def setUp(self):
        self.temporary = TemporaryRepository()
        self.temporary.__enter__()
        self.addCleanup(self.temporary.__exit__, None, None, None)
        self.repo = self.temporary.repo

    def reopen(self):
        """
        Loads the repository from disk in a new instance, which proves persistence.
        """
        reopened = Repository(self.temporary.path, timeout=30)
        self.addCleanup(reopened.close)
        return reopened

    def assert_consistent(self):
        """
        Fails when the repository on disk has any inconsistency.
        """
        problems = audit_repository(self.temporary.path)
        self.assertEqual(problems, {}, describe(problems))

    def assert_saved(self, expected):
        """
        Fails when the index saved on disk does not list exactly the expected files.
        Loading a repository repairs what it reads, so only the raw index proves that a change was saved.
        """
        self.assertEqual(read_index(self.temporary.path), set(expected))

    def test_create_and_reload(self):
        """A created repository is detected and can be loaded again."""
        self.assertTrue(self.repo.is_repository(self.temporary.path))
        self.assertEqual(self.reopen().uniqueName, self.repo.uniqueName)

    def test_load_missing_repository_raises(self):
        """Loading a directory that is not a repository raises."""
        with self.assertRaises(Exception):
            Repository(self.temporary.root)

    def test_dump_pull_roundtrip_for_many_types(self):
        """Python values survive a dump and a pull unchanged."""
        values = {'text': 'hello', 'integer': 7, 'floating': 1.5, 'listing': [1, 'a', None],
                  'mapping': {'k': [1, 2]}, 'raw': b'\x00\x01', 'nothing': None, 'tupled': (1, 2)}
        for name, value in values.items():
            self.assertEqual(self.repo.dump_file(value, name), (True, None))
        reloaded = self.reopen()
        for name, value in values.items():
            self.assertEqual(reloaded.pull_file(name), value, name)
        self.assert_consistent()

    def test_dump_without_replace_refuses_existing_file(self):
        """A second dump of the same file fails unless replace is requested."""
        self.repo.dump_file('first', 'name')
        succeeded, message = self.repo.dump_file('second', 'name', raiseError=False)
        self.assertFalse(succeeded, message)
        self.assertEqual(self.repo.pull_file('name'), 'first')
        self.assertTrue(self.repo.dump_file('second', 'name', replace=True)[0])
        self.assertEqual(self.reopen().pull_file('name'), 'second')

    def test_dump_creates_missing_directories(self):
        """Dumping into a missing directory chain tracks every directory."""
        self.repo.dump_file('v', 'a/b/c/file')
        self.assertEqual(sorted(self.reopen().walk_directories_path(recursive=True)), ['a', 'a/b', 'a/b/c'])
        self.assert_saved(['a/b/c/file'])

    def test_update_file(self):
        """Updating replaces the value and the description."""
        self.repo.dump_file('old', 'name', description='first')
        succeeded, message = self.repo.update_file('new', 'name', description='second')
        self.assertTrue(succeeded, message)
        reloaded = self.reopen()
        self.assertEqual(reloaded.pull_file('name'), 'new')
        self.assertEqual(reloaded.get_file_info('name')[0]['description'], 'second')

    def test_update_untracked_file_fails(self):
        """Updating a file that was never dumped fails."""
        self.assertFalse(self.repo.update_file('v', 'ghost', raiseError=False)[0])

    def test_pull_untracked_file_raises(self):
        """Pulling a file that was never dumped raises."""
        with self.assertRaises(Exception):
            self.repo.pull_file('ghost')

    def test_copy_file_persists(self):
        """A copy exists next to the original after a reload."""
        self.repo.dump_file({'a': 1}, 'src')
        self.assertEqual(self.repo.copy_file('src', 'sub/dst'), (True, None))
        reloaded = self.reopen()
        self.assertEqual(reloaded.pull_file('src'), {'a': 1})
        self.assertEqual(reloaded.pull_file('sub/dst'), {'a': 1})
        self.assert_saved(['src', 'sub/dst'])
        self.assert_consistent()

    def test_rename_file_persists(self):
        """A renamed file only exists under its new name after a reload."""
        self.repo.dump_file('v', 'old')
        self.assertEqual(self.repo.rename_file('old', 'new'), (True, None))
        reloaded = self.reopen()
        self.assertEqual(list(reloaded.walk_files_path()), ['new'])
        self.assertEqual(reloaded.pull_file('new'), 'v')
        self.assert_saved(['new'])
        self.assert_consistent()

    def test_copy_and_rename_onto_themselves_are_refused(self):
        """Copying or renaming a file onto itself never destroys it."""
        self.repo.dump_file('v', 'same')
        self.assertFalse(self.repo.copy_file('same', 'same', force=True, raiseError=False)[0])
        self.assertFalse(self.repo.rename_file('same', 'same', force=True, raiseError=False)[0])
        self.assertEqual(self.repo.pull_file('same'), 'v')

    def test_copy_onto_existing_needs_force(self):
        """Copying over a tracked file needs force."""
        self.repo.dump_file('one', 'a')
        self.repo.dump_file('two', 'b')
        self.assertFalse(self.repo.copy_file('a', 'b', raiseError=False)[0])
        self.assertTrue(self.repo.copy_file('a', 'b', force=True)[0])
        self.assertEqual(self.repo.pull_file('b'), 'one')

    def test_remove_file_persists(self):
        """A removed file is gone from the list and from the disk."""
        self.repo.dump_file('v', 'victim')
        realPath = os.path.join(self.temporary.path, 'victim')
        self.assertEqual(self.repo.remove_file('victim'), (True, ''))
        self.assertFalse(os.path.exists(realPath))
        self.assertEqual(list(self.reopen().walk_files_path()), [])
        self.assert_saved([])
        self.assert_consistent()

    def test_remove_untracked_file_fails(self):
        """Removing a name that is not tracked reports a failure."""
        self.assertFalse(self.repo.remove_file('ghost', raiseError=False)[0])

    def test_add_and_remove_nested_directory(self):
        """A nested directory can be added then removed without touching siblings."""
        self.repo.add_directory('p/gone')
        self.repo.add_directory('p/other')
        self.repo.dump_file('v', 'p/other/file')
        self.assertEqual(self.repo.remove_directory('p/gone'), (True, None))
        reloaded = self.reopen()
        self.assertEqual(sorted(reloaded.walk_directories_path(recursive=True)), ['p', 'p/other'])
        self.assertEqual(reloaded.pull_file('p/other/file'), 'v')

    def test_rename_directory_nested_and_top_level(self):
        """Directories can be renamed at any depth."""
        self.repo.dump_file('v', 'top/inner/file')
        self.assertTrue(self.repo.rename_directory('top/inner', 'renamed')[0])
        self.assertTrue(self.repo.rename_directory('top', 'summit')[0])
        reloaded = self.reopen()
        self.assertEqual(reloaded.pull_file('summit/renamed/file'), 'v')
        self.assert_consistent()

    def test_copy_directory_nested_and_to_root(self):
        """A directory copy brings its files, also when copied to the root."""
        self.repo.dump_file('v', 'src/inner/file')
        self.assertTrue(self.repo.copy_directory('src/inner', 'dst')[0])
        self.assertTrue(self.repo.copy_directory('src', 'srcCopy')[0])
        reloaded = self.reopen()
        self.assertEqual(reloaded.pull_file('dst/file'), 'v')
        self.assertEqual(reloaded.pull_file('srcCopy/inner/file'), 'v')
        self.assert_consistent()

    def test_walk_and_stats(self):
        """Walking, state, stats, representation and string all agree."""
        self.repo.dump_file('v', 'top')
        self.repo.dump_file('v', 'd1/f1')
        self.repo.dump_file('v', 'd1/d2/f2')
        self.assertEqual(sorted(self.repo.walk_files_path(recursive=True)), ['d1/d2/f2', 'd1/f1', 'top'])
        self.assertEqual(sorted(self.repo.walk_files_path('d1')), ['d1/f1'])
        self.assertEqual(self.repo.get_stats(), (2, 3))
        self.assertEqual(self.repo.len, {'number_of_directories': 2, 'number_of_files': 3})
        self.assertIn('[2 directories] [3 files]', repr(self.repo))
        for name in ('top', 'd1', 'f1', 'd2', 'f2'):
            self.assertIn(name, str(self.repo))
        infos = dict(self.repo.walk_files_info(recursive=True))
        self.assertEqual(sorted(infos), ['d1/d2/f2', 'd1/f1', 'top'])
        self.assertTrue(all(isinstance(info, dict) for info in infos.values()))

    def test_file_info_describes_the_dump(self):
        """The info of a file remembers its description and repository."""
        self.repo.dump_file('v', 'name', description='written by test')
        info, message = self.repo.get_file_info('name')
        self.assertEqual(info['description'], 'written by test', message)
        self.assertEqual(info['repository_unique_name'], self.repo.uniqueName)

    def test_custom_dump_and_pull_code(self):
        """Dump and pull can be given as source code."""
        dump = "def dump(path, value):\n    with open(path, 'w') as fd:\n        fd.write(str(value))\n"
        pull = "def pull(path):\n    with open(path) as fd:\n        return int(fd.read())\n"
        self.assertTrue(self.repo.dump_file(41, 'custom', dump=dump, pull=pull)[0])
        self.assertEqual(self.reopen().pull_file('custom'), 41)

    def test_pickle_keywords(self):
        """The pickle keyword and its protocol variants round trip."""
        for keyword in ('pickle', 'pickle2', 'pickle3'):
            self.assertTrue(self.repo.dump_file({'k': keyword}, keyword, dump=keyword)[0], keyword)
            self.assertEqual(self.reopen().pull_file(keyword), {'k': keyword})

    def test_unpicklable_value_fails_cleanly(self):
        """A value that cannot be pickled reports failure and leaves nothing tracked."""
        succeeded, message = self.repo.dump_file(lambda value: value, 'bad', raiseError=False)
        self.assertFalse(succeeded)
        self.assertEqual(list(self.reopen().walk_files_path()), [])

    def test_raise_error_semantics(self):
        """raiseError=True raises Exception, raiseError=False returns a failure tuple."""
        with self.assertRaises(Exception) as caught:
            self.repo.remove_file('ghost')
        self.assertNotIsInstance(caught.exception, AssertionError)
        succeeded, message = self.repo.remove_file('ghost', raiseError=False)
        self.assertFalse(succeeded)
        self.assertTrue(len(message) > 0)

    def test_create_repository_does_not_replace_by_default(self):
        """create_repository refuses to touch an existing repository unless replace=True."""
        self.repo.dump_file('v', 'keep')
        with self.assertRaises(Exception):
            self.repo.create_repository(self.temporary.path)
        self.assertEqual(self.repo.create_repository(self.temporary.path, raiseError=False)[0], False)
        self.assertEqual(self.reopen().pull_file('keep'), 'v')

    def test_package_roundtrip(self):
        """A package unpacks into a repository that holds the same files."""
        self.repo.dump_file('one', 'a/data')
        self.repo.dump_file('two', 'b/data')
        self.repo.create_package()
        archive = os.path.join(self.temporary.root, 'repo.tar')
        unpacked = os.path.join(self.temporary.root, 'unpacked')
        with tarfile.open(archive) as tar:
            self.assertIn('a/data', tar.getnames())
            self.assertIn('b/data', tar.getnames())
            # The data filter is only available on newer Python versions and keeps extraction inside the target
            extractArguments = {'filter': 'data'} if hasattr(tarfile, 'data_filter') else {}
            tar.extractall(unpacked, **extractArguments)
        restored = Repository(unpacked, timeout=30)
        self.addCleanup(restored.close)
        self.assertEqual((restored.pull_file('a/data'), restored.pull_file('b/data')), ('one', 'two'))

    def test_package_names_follow_compression(self):
        """Compressed packages get a .tar.gz name."""
        self.repo.dump_file('v', 'f')
        self.repo.create_package(mode='w:gz')
        self.assertTrue(os.path.isfile(os.path.join(self.temporary.root, 'repo.tar.gz')))

    def test_pickled_instance_with_default_password_keeps_working(self):
        """An instance with the default password survives pickling."""
        import pickle
        self.repo.dump_file('v', 'f')
        clone = pickle.loads(pickle.dumps(self.repo))
        self.addCleanup(clone.close)
        self.assertEqual(clone.pull_file('f'), 'v')

    def test_rename_onto_existing_needs_force(self):
        """Renaming over a tracked file needs force, and force replaces it."""
        self.repo.dump_file('one', 'a')
        self.repo.dump_file('two', 'b')
        self.assertFalse(self.repo.rename_file('a', 'b', raiseError=False)[0])
        self.assertEqual((self.repo.pull_file('a'), self.repo.pull_file('b')), ('one', 'two'))
        self.assertTrue(self.repo.rename_file('a', 'b', force=True)[0])
        self.assertEqual(self.repo.pull_file('b'), 'one')
        self.assert_saved(['b'])

    def test_aliases_do_the_same_as_the_full_names(self):
        """dump, pull and update are aliases of dump_file, pull_file and update_file."""
        self.assertEqual(self.repo.dump('first', 'alias'), (True, None))
        self.assertEqual(self.repo.pull('alias'), 'first')
        self.assertTrue(self.repo.update('second', 'alias')[0])
        self.assertEqual(self.reopen().pull('alias'), 'second')

    def test_properties_and_directory_lists(self):
        """info, uniqueName, locker and the directory list getters describe the repository."""
        with TemporaryRepository() as other:
            other.repo.create_repository(other.path, info={'purpose': 'test'}, replace=True)
            self.assertEqual(other.repo.info, {'purpose': 'test'})
            self.assertTrue(len(other.repo.uniqueName) > 0)
            self.assertTrue(other.repo.locker.isServer)
            other.repo.dump_file('v', 'top')
            other.repo.dump_file('v', 'sub/inner')
            self.assertEqual(sorted(str(item) for item in other.repo.get_repository_directory('')), ['top', "{'sub': ['inner']}"])
            self.assertEqual(other.repo.get_repository_directory('sub'), ['inner'])
            self.assertEqual(other.repo.get_repository_directory('missing'), None)
            self.assertEqual(other.repo.get_repository_parent_directory('sub/inner'), ['inner'])

    def test_walk_directories_info_carries_descriptions(self):
        """Walking directory info yields the description given when each directory was added."""
        self.repo.add_directory('a/b', description='about b')
        infos = dict(self.repo.walk_directories_info(recursive=True))
        self.assertEqual(sorted(infos), ['a', 'a/b'])
        self.assertEqual(infos['a/b']['description'], 'about b')

    @unittest.skipUnless(importlib.util.find_spec('dill'), 'dill is not installed')
    def test_dill_keyword(self):
        """The dill keyword round trips a value."""
        self.assertTrue(self.repo.dump_file({'a': [1, 2]}, 'dilled', dump='dill')[0])
        self.assertEqual(self.reopen().pull_file('dilled'), {'a': [1, 2]})

    @unittest.skipUnless(importlib.util.find_spec('numpy'), 'numpy is not installed')
    def test_numpy_keywords(self):
        """The numpy and numpy_text keywords round trip an array."""
        import numpy
        array = numpy.arange(6, dtype=float).reshape(2, 3)
        for keyword in ('numpy', 'numpy_text'):
            self.assertTrue(self.repo.dump_file(array, keyword, dump=keyword)[0], keyword)
            self.assertTrue(numpy.array_equal(self.reopen().pull_file(keyword), array), keyword)

    def test_update_recreates_a_file_missing_on_disk(self):
        """Updating a tracked file whose data file vanished writes it again."""
        dump = "def dump(path, value):\n    with open(path, 'w') as fd:\n        fd.write(str(value))\n"
        pull = "def pull(path):\n    with open(path) as fd:\n        return fd.read()\n"
        self.repo.dump_file('first', 'name', dump=dump, pull=pull)
        os.remove(os.path.join(self.temporary.path, 'name'))
        succeeded, message = self.repo.update_file('second', 'name', description='again', dump=dump, pull=pull, raiseError=False)
        self.assertTrue(succeeded, message)
        self.assertEqual(self.reopen().pull_file('name'), 'second')

    def test_unattached_instance_warns_and_does_nothing(self):
        """Before create or load, operations warn and return None instead of touching anything."""
        unattached = Repository()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            self.assertIsNone(unattached.dump_file('v', 'name'))
        self.assertTrue(any('create_repository' in str(item.message) for item in caught))

    def test_loading_hides_tracked_files_that_are_missing_on_disk(self):
        """A loaded instance leaves out tracked files whose data file is gone, with a warning, while the saved index still lists them."""
        self.repo.dump_file('v', 'vanishing')
        self.repo.dump_file('v', 'staying')
        os.remove(os.path.join(self.temporary.path, 'vanishing'))
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            loaded = self.reopen()
        self.assertEqual(sorted(loaded.walk_files_path()), ['staying'])
        self.assertTrue(any('vanishing' in str(item.message) for item in caught))
        self.assert_saved(['vanishing', 'staying'])

    def test_remove_repository_removes_only_what_it_tracks(self):
        """remove_repository deletes tracked files and pyrep files, and leaves untracked files and their directory alone."""
        with TemporaryRepository() as other:
            other.repo.dump_file('v', 'sub/tracked')
            stray = os.path.join(other.path, 'stray.txt')
            with open(stray, 'w') as fd:
                fd.write('not mine')
            other.repo.remove_repository(removeEmptyDirs=True)
            self.assertTrue(os.path.isfile(stray))
            self.assertFalse(os.path.exists(os.path.join(other.path, 'sub', 'tracked')))
            self.assertFalse(os.path.exists(os.path.join(other.path, '.pyreprepo')))

    def test_failed_pickle_names_the_offending_attribute(self):
        """When a value cannot be pickled the error names the attribute that is to blame."""
        import threading

        class Holder:
            """
            An object that holds a lock, which cannot be pickled.
            """
            def __init__(self):
                self.fine = 1
                self.guard = threading.Lock()

        succeeded, message = self.repo.dump_file(Holder(), 'holder', raiseError=False)
        self.assertFalse(succeeded)
        self.assertIn('guard', message)
        self.assertNotIn('fine', message)

    def test_pull_with_a_wrong_pull_method_fails_and_releases_the_lock(self):
        """A pull method that raises ends in an error, and the file can be pulled normally afterwards."""
        self.repo.dump_file('value', 'name')
        with self.assertRaises(Exception):
            self.repo.pull_file('name', pull="def pull(path):\n    raise ValueError('broken')\n", ntrials=2)
        self.assertEqual(self.repo.pull_file('name'), 'value')

    def test_failed_update_keeps_the_old_value(self):
        """An update whose value cannot be dumped fails and the file keeps the value it had."""
        self.repo.dump_file('original', 'name')
        succeeded, message = self.repo.update_file(lambda value: value, 'name', raiseError=False)
        self.assertFalse(succeeded)
        self.assertEqual(self.repo.pull_file('name'), 'original')
        self.assertEqual(self.reopen().pull_file('name'), 'original')

    def test_dump_method_that_writes_nothing_is_reported(self):
        """A dump method that does not create its file is an error, and nothing is tracked."""
        dump = "def dump(path, value):\n    pass\n"
        succeeded, message = self.repo.dump_file('v', 'name', dump=dump, raiseError=False)
        self.assertFalse(succeeded)
        self.assertIn('did not create', message)
        self.assertEqual(list(self.reopen().walk_files_path()), [])

    def test_no_temporary_files_are_left_behind(self):
        """After successful and failed writes no temporary file is left in the repository."""
        self.repo.dump_file('v', 'a')
        self.repo.update_file('w', 'a')
        self.repo.dump_file(lambda value: value, 'b', raiseError=False)
        self.repo.copy_file('a', 'c')
        self.repo.rename_file('c', 'd')
        leftovers = [name for _, _, names in os.walk(self.temporary.path) for name in names if name.startswith('.pyreptmp_')]
        self.assertEqual(leftovers, [])

    def test_copy_and_rename_with_force_replace_the_destination(self):
        """Forced copies and renames end with the new content in place."""
        self.repo.dump_file('source', 'src')
        self.repo.dump_file('old copy', 'copied')
        self.repo.dump_file('old moved', 'moved')
        self.assertTrue(self.repo.copy_file('src', 'copied', force=True)[0])
        self.assertTrue(self.repo.rename_file('src', 'moved', force=True)[0])
        reloaded = self.reopen()
        self.assertEqual((reloaded.pull_file('copied'), reloaded.pull_file('moved')), ('source', 'source'))
        self.assertEqual(sorted(reloaded.walk_files_path()), ['copied', 'moved'])

    def test_remove_temporary_files_only_removes_old_leftovers(self):
        """Leftovers of crashed writes are removed once they are old enough, and a recent one is spared."""
        import time
        self.repo.dump_file('v', 'sub/file')
        oldFiles = [os.path.join(self.temporary.path, '.pyreptmp_1_aaaa_.pyreprepo'),
                    os.path.join(self.temporary.path, 'sub', '.pyreptmp_2_bbbb_file')]
        recent   = os.path.join(self.temporary.path, 'sub', '.pyreptmp_3_cccc_file')
        for path in oldFiles + [recent]:
            with open(path, 'wb') as fd:
                fd.write(b'half written')
        past = time.time() - 7200
        for path in oldFiles:
            os.utime(path, (past, past))
        removed = self.repo.remove_temporary_files(olderThan=3600)
        self.assertEqual(sorted(removed), sorted(['.pyreptmp_1_aaaa_.pyreprepo', os.path.join('sub', '.pyreptmp_2_bbbb_file')]))
        self.assertTrue(os.path.isfile(recent))
        self.assertEqual(self.repo.remove_temporary_files(olderThan=0), [os.path.join('sub', '.pyreptmp_3_cccc_file')])
        with self.assertRaises(Exception):
            self.repo.remove_temporary_files(olderThan=-1)
        self.assertEqual(self.repo.pull_file('sub/file'), 'v')

    def test_long_names_keep_working(self):
        """File names close to the limit of the file system still round trip, because temporary names stay short."""
        for length in (100, 200, 230):
            name = 'n' * length
            self.assertEqual(self.repo.dump_file(length, name), (True, None))
            self.assertTrue(self.repo.update_file(length + 1, name)[0])
            self.assertEqual(self.reopen().pull_file(name), length + 1)
        self.assert_consistent()

    def test_name_with_a_null_character_is_refused_clearly(self):
        """A name that no file system accepts raises the same kind of error as other bad paths, and nothing is written."""
        for call in (lambda: self.repo.dump_file('v', 'a\0b', raiseError=False),
                     lambda: self.repo.pull_file('a\0b'),
                     lambda: self.repo.add_directory('a\0b', raiseError=False)):
            with self.assertRaises(Exception) as caught:
                call()
            self.assertNotIsInstance(caught.exception, ValueError)
            self.assertIn('null character', str(caught.exception))
        self.assertEqual(list(self.repo.walk_files_path(recursive=True)), [])
        self.assertFalse(self.repo.is_name_allowed('a\0b')[0])

    def test_rename_works_where_hard_links_are_not_possible(self):
        """When the file system cannot link files, a rename copies them and ends the same."""
        from unittest import mock
        self.repo.dump_file({'a': [1, 2]}, 'src/file', description='kept')
        with mock.patch('os.link', side_effect=OSError('no hard links here')):
            self.assertEqual(self.repo.rename_file('src/file', 'dst/moved'), (True, None))
        reloaded = self.reopen()
        self.assertEqual(reloaded.pull_file('dst/moved'), {'a': [1, 2]})
        self.assertEqual(reloaded.get_file_info('dst/moved')[0]['description'], 'kept')
        self.assertEqual(sorted(reloaded.walk_files_path(recursive=True)), ['dst/moved'])
        self.assertEqual(sorted(name for _, _, names in os.walk(self.temporary.path) for name in names if not name.startswith('.')), ['moved'])

    def test_a_renamed_file_keeps_its_own_content_after_the_old_name_is_reused(self):
        """After a rename the old name can hold a new value without touching the renamed file."""
        self.repo.dump_file('first', 'name')
        self.repo.rename_file('name', 'moved')
        self.repo.dump_file('second', 'name')
        self.repo.update_file('first updated', 'moved')
        reloaded = self.reopen()
        self.assertEqual((reloaded.pull_file('name'), reloaded.pull_file('moved')), ('second', 'first updated'))
        self.assert_consistent()

    def test_removing_a_file_deletes_it_from_disk_after_the_index_is_saved(self):
        """The data, info and class files are all gone from disk once a removal returned."""
        self.repo.dump_file('v', 'sub/gone')
        self.assertEqual(self.repo.remove_file('sub/gone'), (True, ''))
        self.assertEqual([name for name in os.listdir(os.path.join(self.temporary.path, 'sub')) if not name.startswith('.pyrepdirinfo')], [])


if __name__ == '__main__':
    unittest.main()
