"""
Slow tests of failures the environment can cause: a process dying at an exact moment of a write, and the process hosting the lock server going away.
A crash is simulated by a child process that ends itself with os._exit right after pyrep opened the file it is about to write,
which is the state a power loss or a kill leaves behind.
"""
import os
import sys
import shutil
import signal
import pickle
import tempfile
import unittest
import multiprocessing

from pyrep import Repository

from helpers import TemporaryRepository, audit_repository, slow

CRASH_EXIT_CODE = 9


def crashing_writer(path, crashFile, action):
    """
    Process body: performs one write and ends the whole process the moment
    pyrep starts writing the chosen file, after the file was opened and emptied.

    :Parameters:
        #. path (str): The repository path.
        #. crashFile (str): Where to die: on the file 'index', 'info', 'class' or the data file 'data' the moment
           pyrep starts writing it, or inside the commit of several files: 'replace:N' dies as the N-th file is
           about to be moved into place, and 'journal_removal' dies when the commit journal is about to be removed.
        #. action (str): The write to perform: 'dump' of a new file, 'update' of the existing 'keep' file,
           'update_methods' which also changes the dump and pull methods of that file, or 'copy' of 'keep' over 'other'.
    """
    realDump = pickle.dump
    suffixes = {'index': '.pyreprepo', 'info': '_pyrepfileinfo', 'class': '_pyrepfileclass'}

    def crashing_dump(value, fd, *args, **kwargs):
        name = os.path.basename(fd.name)
        # The data file is told apart by its name, written either in place or through a temporary file
        isTemporaryKeep = name.startswith('.pyreptmp_') and name.endswith('_keep')
        isCrashFile = (name == 'keep' or isTemporaryKeep) if crashFile == 'data' else name.endswith(suffixes[crashFile])
        if isCrashFile:
            os._exit(CRASH_EXIT_CODE)
        return realDump(value, fd, *args, **kwargs)

    if crashFile in suffixes or crashFile == 'data':
        pickle.dump = crashing_dump
    repo = Repository(path, timeout=10)
    # These are patched only now, so that loading the repository is not counted
    if crashFile.startswith('replace:'):
        limit       = int(crashFile.split(':')[1])
        realReplace = os.replace
        calls       = []

        def crashing_replace(source, destination):
            calls.append(destination)
            if len(calls) == limit:
                os._exit(CRASH_EXIT_CODE)
            return realReplace(source, destination)

        os.replace = crashing_replace
    elif crashFile.startswith('remove:'):
        limit      = int(crashFile.split(':')[1])
        realRemove = os.remove
        removals   = []

        def crashing_removal(path, *args, **kwargs):
            removals.append(path)
            if len(removals) == limit:
                os._exit(CRASH_EXIT_CODE)
            return realRemove(path, *args, **kwargs)

        os.remove = crashing_removal
    elif crashFile == 'rename':
        realRename = os.rename

        def crashing_rename(source, destination, *args, **kwargs):
            os._exit(CRASH_EXIT_CODE)

        os.rename = crashing_rename
    elif crashFile == 'rmtree':
        def crashing_rmtree(*args, **kwargs):
            os._exit(CRASH_EXIT_CODE)

        shutil.rmtree = crashing_rmtree
    elif crashFile == 'journal_removal':
        realRemove = os.remove

        def crashing_remove(path, *args, **kwargs):
            if str(path).endswith('_pyrepjournal'):
                os._exit(CRASH_EXIT_CODE)
            return realRemove(path, *args, **kwargs)

        os.remove = crashing_remove
    if action == 'dump':
        repo.dump_file('new value', 'victims/new_file')
    elif action == 'update_methods':
        # An update that also changes how the file is stored, which is what makes a mismatch of data and info fatal
        dumpCode = "def dump(path, value):\n    with open(path, 'w') as fd:\n        fd.write(str(value))\n"
        pullCode = "def pull(path):\n    with open(path) as fd:\n        return fd.read()\n"
        repo.update_file('text value', 'keep', description='', dump=dumpCode, pull=pullCode)
    elif action == 'copy':
        repo.copy_file('keep', 'other', force=True)
    elif action == 'rename':
        repo.rename_file('keep', 'sub/renamed')
    elif action == 'remove':
        repo.remove_file('keep')
    elif action == 'remove_directory':
        repo.remove_directory('folder')
    elif action == 'rename_directory':
        repo.rename_directory('folder', 'renamed')
    elif action == 'remove_directory_clean':
        repo.remove_directory('folder', clean=True)
    else:
        repo.update_file('updated value', 'keep')


def lock_server_host(path, ready, stop):
    """
    Process body: creates the repository, which makes this process the lock server host, and
    closes it when told. A host that is killed instead never gets the chance to do that.

    :Parameters:
        #. path (str): The repository path to create.
        #. ready (multiprocessing.Event): Set once the repository exists.
        #. stop (multiprocessing.Event): Waited on before closing the repository.
    """
    repo = Repository(timeout=10)
    repo.create_repository(path)
    ready.set()
    stop.wait(120)
    repo.close()


@unittest.skipIf(sys.platform.startswith('win'), 'needs POSIX process behaviour')
class TestCrashes(unittest.TestCase):
    """
    What is left on disk when a writer dies at an exact moment.
    """

    def setUp(self):
        """
        Creates a temporary repository for every test, it is removed afterwards.
        """
        self.temporary = TemporaryRepository(timeout=10)
        self.temporary.__enter__()
        self.addCleanup(self.temporary.__exit__, None, None, None)
        self.temporary.repo.dump_file('original value', 'keep')

    def crash(self, crashFile, action, path=None):
        """
        Lets a child process die at the chosen moment of a write, in the test repository or in the one at path.

        :Parameters:
            #. crashFile (str): The moment at which the child dies, such as replace:1 or remove:2.
            #. action (str): What the child does, such as dump, update or rename.
            #. path (None, str): The repository to write in, None for the test repository.
        """
        context = multiprocessing.get_context('spawn')
        process = context.Process(target=crashing_writer, args=(self.temporary.path if path is None else path, crashFile, action))
        process.start()
        process.join(60)
        self.assertEqual(process.exitcode, CRASH_EXIT_CODE, 'the child did not crash where it was supposed to')

    def crash_in_the_commit(self, crashFile, action, otherValue=None, extraFiles=()):
        """
        Runs a write that dies at the given moment of its commit in a repository of its own, and returns the path.

        :Parameters:
            #. crashFile (str): The moment at which the child dies.
            #. action (str): What the child does.
            #. otherValue (None, object): The value of a second file to create first, None for no second file.
            #. extraFiles (tuple): Pairs of a name and a value of more files to create first.

        :Returns:
            #. path (str): The path of the repository the child wrote in.
        """
        temporary = TemporaryRepository(timeout=10)
        temporary.__enter__()
        self.addCleanup(temporary.__exit__, None, None, None)
        temporary.repo.dump_file('original value', 'keep')
        if otherValue is not None:
            temporary.repo.dump_file(otherValue, 'other')
        for name, value in extraFiles:
            temporary.repo.dump_file(value, name)
        self.crash(crashFile, action, path=temporary.path)
        return temporary.path

    @slow
    def test_a_crash_inside_the_commit_of_an_update_is_completed_or_undone_whole(self):
        """Dying while the data, info and class files are moved into place leaves the old file or the new one, never a mix."""
        for crashFile in ('replace:1', 'replace:2', 'replace:3', 'replace:4', 'journal_removal'):
            path = self.crash_in_the_commit(crashFile, 'update_methods')
            fresh = Repository(path, timeout=10)
            self.addCleanup(fresh.close)
            expected = 'original value' if crashFile == 'replace:1' else 'text value'
            self.assertEqual(fresh.pull_file('keep'), expected, crashFile)
            self.assertEqual(audit_repository(path), {}, crashFile)

    @slow
    def test_an_interrupted_commit_is_completed_by_the_next_access_when_loading_does_not_clean(self):
        """Without the cleaning at load, the first operation on the file completes the interrupted commit."""
        for crashFile in ('replace:2', 'replace:3'):
            path = self.crash_in_the_commit(crashFile, 'update_methods')
            lazy = Repository(path, timeout=10, removeTemporaryFiles=False)
            self.addCleanup(lazy.close)
            self.assertEqual(len([name for name in os.listdir(path) if name.endswith('_pyrepjournal')]), 1, crashFile)
            self.assertEqual(lazy.pull_file('keep'), 'text value', crashFile)
            self.assertEqual([name for name in os.listdir(path) if name.endswith('_pyrepjournal')], [], crashFile)

    @slow
    def test_a_crash_inside_the_commit_of_a_copy_leaves_the_old_destination_or_the_new_one(self):
        """Forcing a copy over a tracked file and dying while its files are moved leaves the old destination or the new one."""
        for crashFile in ('replace:1', 'replace:2', 'replace:3', 'replace:4'):
            path = self.crash_in_the_commit(crashFile, 'copy', otherValue='other old')
            fresh = Repository(path, timeout=10)
            self.addCleanup(fresh.close)
            expected = 'other old' if crashFile == 'replace:1' else 'original value'
            self.assertEqual(fresh.pull_file('other'), expected, crashFile)
            self.assertEqual(fresh.pull_file('keep'), 'original value', crashFile)
            self.assertEqual(audit_repository(path), {}, crashFile)

    def assert_only_orphans_are_left(self, path):
        """
        Fails when the repository has any inconsistency other than data files that the index no longer lists.
        Those are orphans, which do no harm.

        :Parameters:
            #. path (str): The repository path.
        """
        problems = audit_repository(path)
        problems.pop('on-disk-but-untracked', None)
        self.assertEqual(problems, {})

    def assert_clean_after_a_sweeping_load(self, path):
        """
        Loads the repository in a way that removes orphan files however young, and fails when anything is
        inconsistent afterwards, orphans included.

        :Parameters:
            #. path (str): The repository path.
        """
        sweeper = Repository(timeout=10)
        sweeper.ORPHAN_FILES_MAX_AGE = 0
        sweeper.load_repository(path)
        self.addCleanup(sweeper.close)
        self.assertEqual(audit_repository(path), {})

    def pull_or_none(self, repo, name):
        """
        Pulls a file and returns None when it is not tracked.

        :Parameters:
            #. repo (pyrep.Repository): The instance to pull with.
            #. name (str): The relative path of the file.

        :Returns:
            #. data (None, object): The data of the file, None when it is not tracked.
        """
        try:
            return repo.pull_file(name)
        except Exception:
            return None

    @slow
    def test_a_crash_while_renaming_a_file_never_loses_it(self):
        """Dying at any moment of a rename leaves the file under its old name or its new one, complete, and the index consistent."""
        points = {'replace:1': 'old', 'replace:2': 'old', 'replace:3': 'old', 'replace:4': 'old', 'replace:5': 'old',
                  'remove:1': 'old', 'remove:2': 'new', 'remove:3': 'new', 'remove:4': 'new'}
        for crashFile, where in points.items():
            path = self.crash_in_the_commit(crashFile, 'rename')
            fresh = Repository(path, timeout=10)
            self.addCleanup(fresh.close)
            oldValue, newValue = self.pull_or_none(fresh, 'keep'), self.pull_or_none(fresh, 'sub/renamed')
            if where == 'old':
                self.assertEqual((oldValue, newValue), ('original value', None), crashFile)
            else:
                self.assertEqual((oldValue, newValue), (None, 'original value'), crashFile)
            self.assert_only_orphans_are_left(path)
            self.assert_clean_after_a_sweeping_load(path)

    @slow
    def test_a_crash_while_removing_a_file_never_leaves_a_tracked_file_without_data(self):
        """Dying before the index is saved keeps the file, dying after it removes the file, and in both cases the index is consistent."""
        for crashFile, expected in (('replace:1', 'original value'), ('remove:1', None), ('remove:2', None), ('remove:3', None)):
            path = self.crash_in_the_commit(crashFile, 'remove')
            fresh = Repository(path, timeout=10)
            self.addCleanup(fresh.close)
            self.assertEqual(self.pull_or_none(fresh, 'keep'), expected, crashFile)
            self.assert_only_orphans_are_left(path)
            self.assert_clean_after_a_sweeping_load(path)

    @slow
    def test_a_crash_while_renaming_a_directory_is_completed_or_undone_whole(self):
        """Dying at any moment of a directory rename leaves it under its old name or its new one, with the index agreeing."""
        points = {'replace:1': 'old', 'rename': 'old', 'replace:2': 'new', 'remove:1': 'new'}
        for crashFile, where in points.items():
            path = self.crash_in_the_commit(crashFile, 'rename_directory', extraFiles=[('folder/inner', 'inner value')])
            fresh = Repository(path, timeout=10)
            self.addCleanup(fresh.close)
            oldValue, newValue = self.pull_or_none(fresh, 'folder/inner'), self.pull_or_none(fresh, 'renamed/inner')
            if where == 'old':
                self.assertEqual((oldValue, newValue), ('inner value', None), crashFile)
            else:
                self.assertEqual((oldValue, newValue), (None, 'inner value'), crashFile)
            self.assertFalse(os.path.exists(os.path.join(path, '.pyrepjournal')), crashFile)
            self.assertEqual(audit_repository(path), {}, crashFile)

    @slow
    def test_an_interrupted_directory_rename_is_completed_by_the_next_writer(self):
        """A repository that stays open while another process dies in the middle of a rename is repaired by its next write."""
        for crashFile, newName in (('replace:2', 'renamed'), ('remove:1', 'renamed')):
            temporary = TemporaryRepository(timeout=10)
            temporary.__enter__()
            self.addCleanup(temporary.__exit__, None, None, None)
            temporary.repo.dump_file('inner value', 'folder/inner')
            self.crash(crashFile, 'rename_directory', path=temporary.path)
            self.assertTrue(os.path.exists(os.path.join(temporary.path, '.pyrepjournal')), crashFile)
            self.assertTrue(temporary.repo.dump_file('trigger', 'other', raiseError=False)[0], crashFile)
            self.assertFalse(os.path.exists(os.path.join(temporary.path, '.pyrepjournal')), crashFile)
            fresh = Repository(temporary.path, timeout=10)
            self.addCleanup(fresh.close)
            self.assertEqual(self.pull_or_none(fresh, newName + '/inner'), 'inner value', crashFile)
            self.assertIsNone(self.pull_or_none(fresh, 'folder/inner'), crashFile)
            self.assertEqual(audit_repository(temporary.path), {}, crashFile)

    @slow
    def test_methods_that_only_lock_a_file_complete_an_interrupted_directory_rename(self):
        """A pull or an update on an open repository finds the directory under its new name after another process died in a rename."""
        for operation in ('pull', 'update'):
            temporary = TemporaryRepository(timeout=10)
            temporary.__enter__()
            self.addCleanup(temporary.__exit__, None, None, None)
            temporary.repo.dump_file('inner value', 'folder/inner')
            self.crash('replace:2', 'rename_directory', path=temporary.path)
            self.assertTrue(os.path.exists(os.path.join(temporary.path, '.pyrepjournal')), operation)
            if operation == 'pull':
                self.assertEqual(temporary.repo.pull_file('renamed/inner'), 'inner value')
            else:
                self.assertEqual(temporary.repo.update_file('updated', 'renamed/inner', raiseError=False), (True, ''))
                self.assertEqual(temporary.repo.pull_file('renamed/inner'), 'updated')
            self.assertFalse(os.path.exists(os.path.join(temporary.path, '.pyrepjournal')), operation)

    @slow
    def test_a_crash_while_removing_a_directory_never_leaves_a_tracked_directory_without_files(self):
        """Dying before the index is saved keeps the directory whole, dying after it removes the directory from the index."""
        for crashFile, expected in (('replace:1', 'inner value'), ('rmtree', None)):
            for action in ('remove_directory', 'remove_directory_clean'):
                path = self.crash_in_the_commit(crashFile, action, extraFiles=[('folder/inner', 'inner value')])
                fresh = Repository(path, timeout=10)
                self.addCleanup(fresh.close)
                self.assertEqual(self.pull_or_none(fresh, 'folder/inner'), expected, (crashFile, action))
                self.assertEqual(fresh.pull_file('keep'), 'original value')
                self.assert_only_orphans_are_left(path)
                self.assert_clean_after_a_sweeping_load(path)

    @slow
    def test_crash_before_registration_leaves_a_usable_repository(self):
        """A writer dying after its data was written but before it was registered leaves at most unregistered files."""
        self.crash('class', 'dump')
        fresh = Repository(self.temporary.path, timeout=10)
        self.addCleanup(fresh.close)
        self.assertEqual(fresh.pull_file('keep'), 'original value')
        self.assertEqual(list(fresh.walk_files_path('victims')), [])
        self.assertFalse(os.path.exists(os.path.join(self.temporary.path, 'victims', 'new_file')))
        self.assertTrue(fresh.dump_file('written again', 'victims/new_file', raiseError=False)[0])
        self.assertEqual(fresh.pull_file('victims/new_file'), 'written again')

    @slow
    def test_crash_while_saving_the_index_keeps_the_repository_loadable(self):
        """A writer dying while it saves the repository index leaves the previous index usable."""
        self.crash('index', 'dump')
        fresh = Repository(self.temporary.path, timeout=10)
        self.addCleanup(fresh.close)
        self.assertEqual(fresh.pull_file('keep'), 'original value')

    @slow
    def test_crash_while_writing_data_keeps_the_old_value(self):
        """A writer dying in the middle of writing the data of an update leaves the previous value complete."""
        self.crash('data', 'update')
        fresh = Repository(self.temporary.path, timeout=10)
        self.addCleanup(fresh.close)
        self.assertEqual(fresh.pull_file('keep'), 'original value')

    @slow
    def test_crash_while_saving_file_info_keeps_the_file_readable(self):
        """A writer dying while it updates the info of a file leaves that file readable."""
        self.crash('info', 'update')
        fresh = Repository(self.temporary.path, timeout=10)
        self.addCleanup(fresh.close)
        self.assertEqual(fresh.pull_file('keep'), 'original value')

    @slow
    def test_crash_while_updating_with_new_methods_keeps_data_and_info_together(self):
        """A crash while an update changes how a file is stored leaves the old data with the old info, which still match."""
        self.crash('info', 'update_methods')
        fresh = Repository(self.temporary.path, timeout=10)
        self.addCleanup(fresh.close)
        self.assertEqual(fresh.pull_file('keep'), 'original value')


class TestLockServerHost(unittest.TestCase):
    """
    The process that created the repository hosts the lock server for everybody else.
    """

    @slow
    def test_clients_survive_the_lock_server_host_leaving(self):
        """After the lock server host exits, a client can still lock and write."""
        context = multiprocessing.get_context('spawn')
        root    = tempfile.mkdtemp(prefix='pyrep_test_')
        self.addCleanup(shutil.rmtree, root, True)
        path  = os.path.join(root, 'repo')
        ready = context.Event()
        stop  = context.Event()
        host  = context.Process(target=lock_server_host, args=(path, ready, stop))
        host.start()
        self.assertTrue(ready.wait(60))
        client = Repository(path, timeout=3)
        self.assertTrue(client.dump_file('before', 'before', raiseError=False)[0])
        stop.set()
        host.join(30)
        self.assertTrue(client.dump_file('after', 'after', raiseError=False)[0])

    @slow
    def test_clients_survive_the_lock_server_host_being_killed(self):
        """After the lock server host is killed, a client takes its place, which needs a few seconds for the dead server to expire."""
        context = multiprocessing.get_context('spawn')
        root    = tempfile.mkdtemp(prefix='pyrep_test_')
        self.addCleanup(shutil.rmtree, root, True)
        path  = os.path.join(root, 'repo')
        ready = context.Event()
        stop  = context.Event()
        host  = context.Process(target=lock_server_host, args=(path, ready, stop))
        host.start()
        self.assertTrue(ready.wait(60))
        client = Repository(path, timeout=15)
        self.assertTrue(client.dump_file('before', 'before', raiseError=False)[0])
        os.kill(host.pid, signal.SIGKILL)
        host.join(30)
        written, message = client.dump_file('after', 'after', raiseError=False)
        self.assertTrue(written, message)
        self.assertEqual(client.pull_file('before'), 'before')


if __name__ == '__main__':
    unittest.main()
