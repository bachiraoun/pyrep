"""
An instance that does not find a name looks at the index again, once, when another instance or process saved it
after this instance read it. Finding a name never costs a lock.
"""
import os
import time
import threading
import multiprocessing
import unittest
from unittest import mock

from pyrep import Repository

from helpers import LOCK_TIMEOUT, TemporaryRepository, audit_repository, check_record, make_record


def late_writer(path, count, resultQueue):
    """
    Process body: adds files one after the other, pausing between them so that readers see the index change.

    :Parameters:
        #. path (str): The repository path.
        #. count (int): Number of files to add.
        #. resultQueue (multiprocessing.Queue): Receives the number of files that were added.
    """
    repo = Repository(path, timeout=LOCK_TIMEOUT)
    added = 0
    for index in range(count):
        succeeded, _ = repo.dump_file(make_record('late', index), f'late/f{index}', raiseError=False)
        added += 1 if succeeded else 0
        time.sleep(0.05)
    repo.close()
    resultQueue.put(added)


def late_reader(path, count, resultQueue):
    """
    Process body: waits for every file of the late writer by pulling it, with no refresh call of its own.

    :Parameters:
        #. path (str): The repository path.
        #. count (int): Number of files to wait for.
        #. resultQueue (multiprocessing.Queue): Receives the number of files that were read intact.
    """
    repo = Repository(path, timeout=LOCK_TIMEOUT)
    found = 0
    deadline = time.time() + 120
    for index in range(count):
        while time.time() < deadline:
            try:
                record = repo.pull_file(f'late/f{index}')
            except Exception:
                time.sleep(0.02)
                continue
            found += 1 if check_record(record)[0] else 0
            break
    repo.close()
    resultQueue.put(found)


class TestStaleView(unittest.TestCase):
    """
    Two instances of the same repository, one of them writing and the other one reading.
    """

    def setUp(self):
        """
        Creates a temporary repository for every test, it is removed afterwards.
        """
        self.temporary = TemporaryRepository()
        self.temporary.__enter__()
        self.addCleanup(self.temporary.__exit__, None, None, None)
        self.writer = self.temporary.repo
        self.reader = Repository(self.temporary.path, timeout=LOCK_TIMEOUT)
        self.addCleanup(self.reader.close)

    def test_a_new_file_is_found_by_every_read_method(self):
        """Pulling, the info, the existence check and the listings find a file that another instance added."""
        self.writer.dump_file(make_record('w', 1), 'dir/new', description='from the writer')
        self.assertEqual(self.reader.pull_file('dir/new'), make_record('w', 1))
        self.assertEqual(self.reader.get_file_info('dir/new')[0]['description'], 'from the writer')
        self.assertTrue(self.reader.is_repository_file('dir/new')[0])
        self.assertTrue(self.reader.is_repository_directory('dir'))
        self.assertEqual(list(self.reader.walk_files_path('dir')), ['dir/new'])
        self.assertEqual(list(self.reader.walk_directories_path()), ['dir'])
        self.assertEqual(self.reader.get_repository_directory('dir'), ['new'])
        self.assertEqual(self.reader.get_repository_parent_directory('dir/new'), ['new'])
        self.assertIn('dir/new', [name for item in self.reader.get_repository_state('dir') for name in item])

    def test_known_names_never_refresh(self):
        """Reading a name that the instance already knows does not look at the index again."""
        self.writer.dump_file('value', 'known')
        self.reader.refresh_repository()
        with mock.patch.object(self.reader, 'refresh_repository', wraps=self.reader.refresh_repository) as spy:
            self.assertEqual(self.reader.pull_file('known'), 'value')
            self.assertTrue(self.reader.is_repository_file('known')[0])
            self.assertEqual(spy.call_count, 0)

    def test_missing_name_with_an_unchanged_index_never_refreshes(self):
        """A name that does not exist costs one stat and no lock while nobody saved the index."""
        self.reader.refresh_repository()
        with mock.patch.object(self.reader, 'refresh_repository', wraps=self.reader.refresh_repository) as spy:
            for _ in range(5):
                self.assertFalse(self.reader.is_repository_file('absent')[0])
                self.assertFalse(self.reader.is_repository_directory('absent'))
            self.assertEqual(spy.call_count, 0)

    def test_one_refresh_serves_every_later_miss(self):
        """After one reload the instance is up to date, so later misses on absent names do not reload again."""
        self.writer.dump_file('value', 'new')
        with mock.patch.object(self.reader, 'refresh_repository', wraps=self.reader.refresh_repository) as spy:
            self.assertTrue(self.reader.is_repository_file('new')[0])
            self.assertFalse(self.reader.is_repository_file('absent')[0])
            self.assertFalse(self.reader.is_repository_file('absent')[0])
            self.assertEqual(spy.call_count, 1)

    def test_own_save_counts_as_up_to_date(self):
        """An instance that saved the index itself does not reload it when a name is missing."""
        self.reader.dump_file('value', 'mine')
        with mock.patch.object(self.reader, 'refresh_repository', wraps=self.reader.refresh_repository) as spy:
            self.assertFalse(self.reader.is_repository_file('absent')[0])
            self.assertEqual(spy.call_count, 0)

    def test_orphan_scan_does_not_hide_a_change(self):
        """Reading the index to look for orphans does not make the instance believe that it is up to date."""
        self.writer.dump_file('value', 'new')
        self.reader.remove_orphan_files()
        self.assertEqual(self.reader.pull_file('new'), 'value')

    def test_a_file_removed_by_another_instance_is_not_a_repository_file(self):
        """A name that another instance removed is reported as not a repository file, not as one missing on disk."""
        self.writer.dump_file('value', 'gone')
        self.reader.refresh_repository()
        self.writer.remove_file('gone')
        self.assertEqual(self.reader.is_repository_file('gone'), (False, False, False, False))
        self.assertIsNone(self.reader.get_file_info('gone')[0])
        self.assertEqual(self.reader.get_file_info('gone')[1], 'file is not a registered repository file.')
        with self.assertRaisesRegex(Exception, 'is not a repository file'):
            self.reader.pull_file('gone')

    def test_a_missing_info_file_with_an_unchanged_index_keeps_its_message(self):
        """Damage that nobody caused through the index is still reported as it is, without reloading."""
        self.writer.dump_file('value', 'damaged')
        self.reader.refresh_repository()
        os.remove(os.path.join(self.temporary.path, '.damaged_pyrepfileinfo'))
        with mock.patch.object(self.reader, 'refresh_repository', wraps=self.reader.refresh_repository) as spy:
            self.assertEqual(self.reader.get_file_info('damaged')[1], 'file is a registered repository file but info file missing')
            self.assertEqual(spy.call_count, 0)

    def test_a_file_renamed_by_another_instance_is_followed(self):
        """The old name of a renamed file is gone and the new name is found by an instance with an old list."""
        self.writer.dump_file('value', 'before')
        self.reader.refresh_repository()
        self.writer.rename_file('before', 'after')
        self.assertFalse(self.reader.is_repository_file('before')[0])
        self.assertEqual(self.reader.pull_file('after'), 'value')

    def test_deleted_names_stay_listed_until_refreshed(self):
        """Names that others removed are not noticed by a lookup that finds them, a refresh is still needed."""
        self.writer.dump_file('value', 'doomed')
        self.reader.refresh_repository()
        self.writer.remove_file('doomed')
        self.assertEqual(list(self.reader.walk_files_path()), ['doomed'])
        self.reader.refresh_repository()
        self.assertEqual(list(self.reader.walk_files_path()), [])

    def test_writers_with_a_stale_view_still_work(self):
        """Methods holding locks never refresh, and they still see what others saved."""
        self.writer.dump_file('value', 'a/one')
        self.reader.dump_file('value', 'a/two')
        self.reader.copy_file('a/one', 'a/three')
        self.reader.rename_file('a/three', 'a/four')
        self.reader.remove_file('a/two')
        self.writer.refresh_repository()
        self.assertEqual(sorted(self.writer.walk_files_path('a')), ['a/four', 'a/one'])
        self.assertEqual(audit_repository(self.temporary.path), {})

    def test_misses_from_many_threads_while_others_write(self):
        """Threads that miss names while another instance keeps saving never deadlock or fail."""
        stop     = threading.Event()
        failures = []

        def writer_loop():
            for index in range(15):
                self.writer.dump_file(make_record('w', index), f'burst/f{index}')
            stop.set()

        def reader_loop():
            while not stop.is_set():
                try:
                    self.reader.is_repository_file('burst/nothing')
                    self.reader.pull_file('burst/f0') if self.reader.is_repository_file('burst/f0')[0] else None
                except Exception as err:
                    failures.append(str(err)[:100])

        threads = [threading.Thread(target=writer_loop)] + [threading.Thread(target=reader_loop) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=120)
            self.assertFalse(thread.is_alive(), 'a thread is stuck')
        self.assertEqual(failures, [])
        # A listing never reloads by itself, so the reader asks for it before counting
        self.reader.refresh_repository()
        self.assertEqual(len(list(self.reader.walk_files_path('burst'))), 15)

    def test_a_reader_process_sees_files_added_by_a_writer_process(self):
        """A process that never refreshes finds every file another process adds while it waits for it."""
        context = multiprocessing.get_context('spawn')
        queue   = context.Queue()
        procs   = [context.Process(target=late_writer, args=(self.temporary.path, 10, queue)),
                   context.Process(target=late_reader, args=(self.temporary.path, 10, queue))]
        for proc in procs:
            proc.start()
        counts = [queue.get(timeout=150) for _ in procs]
        for proc in procs:
            proc.join(timeout=10)
        self.assertEqual(counts, [10, 10])


if __name__ == '__main__':
    unittest.main()
