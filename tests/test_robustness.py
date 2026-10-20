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

from helpers import TemporaryRepository, slow

CRASH_EXIT_CODE = 9


def crashing_writer(path, crashFile, action):
    """
    Process body: performs one write and ends the whole process the moment
    pyrep starts writing the chosen file, after the file was opened and emptied.

    :Parameters:
        #. path (str): The repository path.
        #. crashFile (str): Which file to die on, one of 'index', 'info', 'class' or the data file 'data'.
        #. action (str): The write to perform, either 'dump' of a new file or 'update' of the existing 'keep' file.
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

    pickle.dump = crashing_dump
    repo = Repository(path, timeout=10)
    if action == 'dump':
        repo.dump_file('new value', 'victims/new_file')
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
        self.temporary = TemporaryRepository(timeout=10)
        self.temporary.__enter__()
        self.addCleanup(self.temporary.__exit__, None, None, None)
        self.temporary.repo.dump_file('original value', 'keep')

    def crash(self, crashFile, action):
        """
        Lets a child process die while it writes the chosen file.
        """
        context = multiprocessing.get_context('spawn')
        process = context.Process(target=crashing_writer, args=(self.temporary.path, crashFile, action))
        process.start()
        process.join(60)
        self.assertEqual(process.exitcode, CRASH_EXIT_CODE, 'the child did not crash where it was supposed to')

    @slow
    def test_crash_before_registration_leaves_a_usable_repository(self):
        """A writer dying after its data was written but before it was registered leaves at most unregistered files."""
        self.crash('class', 'dump')
        fresh = Repository(self.temporary.path, timeout=10)
        self.addCleanup(fresh.close)
        self.assertEqual(fresh.pull_file('keep'), 'original value')
        self.assertEqual(list(fresh.walk_files_path('victims')), [])
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
        self.assertIn(fresh.pull_file('keep'), ('original value', 'updated value'))


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
