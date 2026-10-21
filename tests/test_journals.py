"""
Tests of the shared journal mechanism: the format, the kinds, and what happens with journals that cannot be completed.
"""
import os
import pickle
import warnings
import unittest
import importlib

from pyrep import Repository

from helpers import TemporaryRepository, audit_repository

module = importlib.import_module('pyrep.Repository')


class TestJournalFormat(unittest.TestCase):
    """
    What a journal file holds and how it is read.
    """

    def setUp(self):
        """
        Creates a temporary repository for every test, it is removed afterwards.
        """
        self.temporary = TemporaryRepository(timeout=3)
        self.temporary.__enter__()
        self.addCleanup(self.temporary.__exit__, None, None, None)
        self.path = os.path.join(self.temporary.root, 'journal')

    def test_a_journal_gives_back_its_kind_and_its_data(self):
        """What is written is what is read, and writing is atomic, so no temporary file stays."""
        module.write_journal(self.path, 'file_moves', [('a', 'b')], 4)
        self.assertEqual(module.read_journal(self.path), ('file_moves', [('a', 'b')]))
        self.assertEqual([name for name in os.listdir(self.temporary.root) if name.startswith('.pyreptmp_')], [])

    def test_a_file_that_is_not_a_journal_is_refused(self):
        """Anything that is not a record with a kind and data raises."""
        for content in ([('a', 'b')], {'kind': 'x'}, 'text', {'kind': 'x', 'data': 1, 'more': 2}):
            with open(self.path, 'wb') as fd:
                pickle.dump(content, fd)
            with self.assertRaises(Exception):
                module.read_journal(self.path)

    def test_file_moves_are_finished_once_and_repeatably(self):
        """Finishing moves what is left to move, skips what already moved, and removes the journal."""
        directory = self.temporary.root
        for name in ('.tmp_one', '.tmp_two'):
            with open(os.path.join(directory, name), 'w') as fd:
                fd.write(name)
        with open(os.path.join(directory, 'two'), 'w') as fd:
            fd.write('old two')
        module.write_journal(self.path, 'file_moves', [('.tmp_one', 'one'), ('.tmp_two', 'two')], 4)
        os.replace(os.path.join(directory, '.tmp_one'), os.path.join(directory, 'one'))
        module.finish_file_moves(self.path)
        self.assertEqual(open(os.path.join(directory, 'one')).read(), '.tmp_one')
        self.assertEqual(open(os.path.join(directory, 'two')).read(), '.tmp_two')
        self.assertFalse(os.path.exists(self.path))

    def test_finishing_moves_refuses_another_kind(self):
        """A journal of another kind is not treated as moves."""
        module.write_journal(self.path, 'rename_directory', {}, 4)
        with self.assertRaises(Exception):
            module.finish_file_moves(self.path)


class TestRepositoryJournal(unittest.TestCase):
    """
    The journal of the repository directory and the way a lock completes it.
    """

    def setUp(self):
        """
        Creates a temporary repository for every test, it is removed afterwards.
        """
        self.temporary = TemporaryRepository(timeout=0.1)
        self.temporary.__enter__()
        self.addCleanup(self.temporary.__exit__, None, None, None)
        self.repo        = self.temporary.repo
        self.journalPath = os.path.join(self.temporary.path, '.pyrepjournal')
        self.repo.dump_file('v', 'folder/inner')

    def test_an_unknown_kind_blocks_writers_with_a_clear_message_until_it_is_removed(self):
        """A journal that nothing knows how to complete stops writes, says why, and writing works again once it is gone."""
        module.write_journal(self.journalPath, 'a_kind_from_the_future', {}, 4)
        succeeded, message = self.repo.dump_file('v', 'other', raiseError=False)
        self.assertFalse(succeeded)
        self.assertIn('unknown kind', message)
        os.remove(self.journalPath)
        self.assertTrue(self.repo.dump_file('v', 'other', raiseError=False)[0])

    def test_a_rename_that_cannot_be_decided_warns_and_is_dropped(self):
        """When neither directory of an interrupted rename exists, the journal is removed with a warning and writing continues."""
        module.write_journal(self.journalPath, 'rename_directory', {'parent': '', 'old': 'nothing', 'new': 'nowhere'}, 4)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            self.assertTrue(self.repo.dump_file('v', 'other', raiseError=False)[0])
        self.assertTrue(any('cannot be decided' in str(item.message) for item in caught))
        self.assertFalse(os.path.exists(self.journalPath))

    def test_a_rename_that_never_happened_is_discarded_silently(self):
        """When the old directory is still there the journal is just removed."""
        module.write_journal(self.journalPath, 'rename_directory', {'parent': '', 'old': 'folder', 'new': 'renamed'}, 4)
        self.assertTrue(self.repo.dump_file('v', 'other', raiseError=False)[0])
        self.assertFalse(os.path.exists(self.journalPath))
        self.assertEqual(self.repo.pull_file('folder/inner'), 'v')

    def test_a_finished_rename_makes_the_index_follow(self):
        """When the directory is renamed on disk and the index still has the old name, taking the lock fixes the index."""
        os.rename(os.path.join(self.temporary.path, 'folder'), os.path.join(self.temporary.path, 'renamed'))
        module.write_journal(self.journalPath, 'rename_directory', {'parent': '', 'old': 'folder', 'new': 'renamed'}, 4)
        self.assertTrue(self.repo.dump_file('v', 'other', raiseError=False)[0])
        reloaded = Repository(self.temporary.path, timeout=3)
        self.addCleanup(reloaded.close)
        self.assertEqual(reloaded.pull_file('renamed/inner'), 'v')
        self.assertEqual(audit_repository(self.temporary.path), {})

    def test_the_journal_name_is_reserved(self):
        """The journal name cannot be used for user data."""
        self.assertFalse(self.repo.is_name_allowed('.pyrepjournal')[0])
        self.assertFalse(self.repo.dump_file('v', '.pyrepjournal', raiseError=False)[0])


if __name__ == '__main__':
    unittest.main()
