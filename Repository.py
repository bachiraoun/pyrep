"""
Usage:
======

.. code-block:: python

    import os
    import numpy as np
    from pyrep import Repository

    # any directory can be a repository
    PATH = os.path.join(os.path.expanduser("~"), 'pyrepTest_canBeDeleted')

    REP = Repository()
    print(REP.path)     # None, nothing is created or loaded yet
    success, message = REP.create_repository(PATH, replace=True)    # replace=True erases PATH when it already is a repository
    print(success)

    REP.add_directory("folder1/folder2/folder3")
    REP.add_directory("directory1/directory2")

    REP.dump("This is a string to pickle and store in the repository", 'pickled')
    REP.dump([1, 2, 3], "folder1/folder2/folder3/list.pkl")

    dump = "import numpy as np; dump = lambda path, value: np.savetxt(fname=path, X=value, fmt='%.6e')"
    pull = "import numpy as np; pull = lambda path: np.loadtxt(fname=path)"
    REP.dump(np.array([0.5, 0.25, 0.125]), 'text.dat', dump=dump, pull=pull)

    print(REP.pull('text.dat'))
    print(REP.pull("folder1/folder2/folder3/list.pkl"))

    REP.update("This is an updated string", 'pickled')
    print(REP.pull('pickled'))
    REP.copy_file('pickled', 'directory1/copy')
    REP.rename_file('directory1/copy', 'directory1/renamed')
    REP.remove_file('directory1/renamed')

    for f in REP.walk_files_path(recursive=True):
        print(f)
    for d in REP.walk_directories_path(recursive=True):
        print(d)
    print(REP)
    print(repr(REP))

    REP.create_package()    # a tar file of the repository, created next to it
    print(sorted(n for n in os.listdir(ROOT)))

    other = Repository(PATH)
    REP.dump("added later", 'late')
    print('late' in list(other.walk_files_path()))
    other.refresh_repository()    # a listing only shows what others added after a refresh, pulling a name it does not know reloads by itself
    print('late' in list(other.walk_files_path()))
    other.close()

    REP.remove_repository(removeEmptyDirs=True)
    print(REP.is_repository(PATH))


output
======

.. code-block:: python

    None
    True
    [0.5   0.25  0.125]
    [1, 2, 3]
    This is an updated string
    pickled
    text.dat
    folder1/folder2/folder3/list.pkl
    folder1
    directory1
    folder1/folder2
    folder1/folder2/folder3
    directory1/directory2
    /home/user/pyrepTest_canBeDeleted
      pickled
      text.dat
      /directory1
        /directory2
      /folder1
        /folder2
          /folder3
          list.pkl
    pyrep Repository (Version 4.0.0) @/home/user/pyrepTest_canBeDeleted [5 directories] [3 files] 
    ['pyrepTest_canBeDeleted', 'pyrepTest_canBeDeleted.tar']
    False
    True
    False


Errors
======
Every method that can fail takes a *raiseError* argument. With the default ``True`` a failure raises an
``Exception``. With ``False`` the method returns a tuple of a success flag and a message instead.


Concurrency and crashes
=======================
Threads and processes can use the same repository at the same time. Access is coordinated by
`pylocker <https://pypi.org/project/pylocker/>`_ locks. The repository index and the info files are
written to a temporary file and then renamed into place, and so are data files, which means a crash
leaves the previous content complete. Leftover temporary files of crashed writes are removed with
:py:meth:`~pyrep.Repository.Repository.remove_temporary_files`, and the files that a crashed operation left in the
repository without the index listing them are removed with :py:meth:`~pyrep.Repository.Repository.remove_orphan_files`.
Loading a repository does both by default, for the files that were not touched for an hour, and the flags
*removeTemporaryFiles* and *removeOrphanFiles* turn it off. Operations that need several steps, such as renaming a
directory, write a journal first, and whoever takes the lock next completes what a crash interrupted.
If the process hosting the lock server exits, the next operation of another process takes its place.
"""

# standard distribution imports
import os, sys, re, time, uuid, errno, random, warnings, tarfile, shutil, traceback, inspect, threading, weakref
from functools import wraps
import copy
import pickle

# import pylocker ServerLocker singleton implementation
from pylocker import FACTORY

# pyrep imports
from .__pkginfo__ import __version__

# Every instance of a process that works on the same repository shares one locker, so the locker may only
# be stopped when the last of those instances is closed. Keys are server file paths.
LOCKER_USERS       = {}
LOCKER_USERS_MUTEX = threading.RLock()

# An operation that fails is only attempted again when the error can pass by itself. These are the codes of
# such errors, the pause before the next attempt starts at the base delay and doubles up to the maximum.
TRANSIENT_ERRNOS = frozenset(getattr(errno, name) for name in ('EINTR', 'EAGAIN', 'EBUSY', 'ETXTBSY', 'ESTALE', 'ETIMEDOUT', 'EMFILE', 'ENFILE')
                             if hasattr(errno, name))
RETRY_BASE_DELAY = 0.05
RETRY_MAX_DELAY  = 1.0

# set warnings filter to always
warnings.simplefilter('always')


def is_transient_error(err):
    """
    Tells whether an error can pass by itself, which makes the operation worth another attempt. Only operating
    system errors such as a busy or interrupted call qualify, and on Windows a refused access, which is what a file
    held for a moment by an antivirus or an indexer looks like. The error an operation was wrapped in is
    looked at too. Errors of logic, of values and errors raised by user code that are not of this kind are never transient.

    :Parameters:
        #. err (Exception): The error of a failed attempt.

    :Returns:
        #. isTransient (bool): Whether another attempt can succeed.
    """
    seen = set()
    while err is not None and id(err) not in seen:
        seen.add(id(err))
        if isinstance(err, (InterruptedError, BlockingIOError, TimeoutError)):
            return True
        if isinstance(err, OSError):
            if err.errno in TRANSIENT_ERRNOS:
                return True
            if os.name == 'nt' and isinstance(err, PermissionError):
                return True
        err = err.__cause__
    return False


def should_retry(err, trial, ntrials):
    """
    Decides whether a failed attempt is followed by another one and, if so, pauses first. The pause starts at
    RETRY_BASE_DELAY seconds, doubles with every attempt up to RETRY_MAX_DELAY, and is shortened by up to half
    at random so that processes that failed together do not retry together.

    :Parameters:
        #. err (Exception): The error of the failed attempt.
        #. trial (int): The index of the failed attempt, starting at 0.
        #. ntrials (int): The maximum number of attempts.

    :Returns:
        #. retry (bool): Whether another attempt must be made.
    """
    if trial >= ntrials - 1 or not is_transient_error(err):
        return False
    time.sleep(min(RETRY_BASE_DELAY * 2 ** trial, RETRY_MAX_DELAY) * (0.5 + random.random() / 2))
    return True


def describe_attempts(attempts):
    """
    Describes the errors of all the attempts of an operation.

    :Parameters:
        #. attempts (list): The error text of every attempt so far.

    :Returns:
        #. description (str): The only error, or every attempt's error numbered.
    """
    if len(attempts) == 1:
        return attempts[0]
    return '; '.join('attempt %i: %s'%(index + 1, text) for index, text in enumerate(attempts))


def get_pickling_errors(obj, seen=None):
    """
    Investigates why an object cannot be pickled by looking for the attributes that cannot be pickled.

    :Parameters:
        #. obj (object): The object that failed to pickle.
        #. seen (None, list): Attribute values already investigated, which stops endless recursion.

    :Returns:
        #. errors (None, str, dict): None when the object has no state to look at, a message when its
           state is empty or unreadable, otherwise a dictionary of attribute name to the investigation
           of that attribute.
    """
    if seen is None:
        seen = []
    try:
        if hasattr(obj, "__getstate__"):
            state = obj.__getstate__()
        elif hasattr(obj, "__dict__"):
            # object.__getstate__ only exists from python 3.11
            state = dict(vars(obj))
        else:
            return None
    except Exception as err:
        return 'unable to read the object state (%s)'%str(err)
    if state is None:
        return 'object state is None'
    if isinstance(state, tuple):
        merged = {}
        for part in state:
            if isinstance(part, dict):
                merged.update(part)
        state = merged
    result = {}
    for name in state:
        try:
            pickle.dumps(state[name], protocol=2)
        except Exception:
            if not any(state[name] is item for item in seen):
                seen.append(state[name])
                result[name] = get_pickling_errors(state[name], seen)
    return result


def parse_pickle_protocol(text):
    """
    Reads the protocol number of a pickle or dill keyword such as the 2 of 'pickle2'.

    :Parameters:
        #. text (str): The protocol number as text.

    :Returns:
        #. protocol (int): The protocol, at least -1.

    :Raises:
        #. Exception: If text is not an integer or is smaller than -1.
    """
    try:
        protocol = int(text)
    except ValueError:
        raise Exception("protocol must be an integer >=-1")
    if protocol < -1:
        raise Exception("protocol must be an integer >=-1")
    return protocol



def get_dump_method(dump, protocol=-1):
    """
    Gets the source code of the function that dumps a value to a file.

    :Parameters:
        #. dump (None, str): None or 'pickle' dump with pickle, 'pickleN' and 'dillN' choose a protocol N,
           'dill', 'json', 'numpy' and 'numpy_text' are the other keywords. Any other string is taken as
           source code that defines `dump(path, value)` and is returned as given.
        #. protocol (int): The pickle protocol used by the 'pickle' keyword.

    :Returns:
        #. code (str): Source code that defines `dump(path, value)`.
    """
    if dump is None:
        dump = 'pickle'
    if dump.startswith('pickle'):
        if dump == 'pickle':
            proto = protocol
        else:
            proto = dump.strip('pickle')
        proto = parse_pickle_protocol(proto)
        code = """
def dump(path, value):
    import os, pickle
    with open(path, 'wb') as fd:
        pickle.dump( value, fd, protocol=%i )
        fd.flush()
        os.fsync(fd.fileno())
"""%proto
    elif dump.startswith('dill'):
        if dump == 'dill':
            proto = 4
        else:
            proto = dump.strip('dill')
            proto = parse_pickle_protocol(proto)
        code = """
def dump(path, value):
    import dill, os
    with open(path, 'wb') as fd:
        dill.dump( value, fd, protocol=%i )
        fd.flush()
        os.fsync(fd.fileno())
"""%proto
    elif dump == 'json':
        code = """
def dump(path, value):
    import json, os
    with open(path, 'w') as fd:
        json.dump( value,fd, ensure_ascii=True, indent=4 )
        fd.flush()
        os.fsync(fd.fileno())
"""
    elif dump == 'numpy':
        code = """
def dump(path, value):
    import numpy, os
    with open(path, 'wb') as fd:
        numpy.save(file=fd, arr=value)
        fd.flush()
        os.fsync(fd.fileno())
"""
    elif dump == 'numpy_text':
        code = """
def dump(path, value):
    import numpy
    numpy.savetxt(fname=path, X=value, fmt='%.6e')
"""
    else:
        if not (isinstance(dump, str)):
            raise Exception("dump must be None or a string")
        code = dump
    # return
    return code




def get_pull_method(pull):
    """
    Gets the source code of the function that pulls a value from a file.

    :Parameters:
        #. pull (None, str): None or a keyword starting with 'pickle', 'dill', 'json', 'numpy' or
           'numpy_text'. Any other string is taken as source code that defines `pull(path)` and is
           returned as given.

    :Returns:
        #. code (str): Source code that defines `pull(path)`.
    """
    if pull is None or pull.startswith('pickle'):
        code = """
def pull(path):
    import pickle
    with open(path, 'rb') as fd:
        return pickle.load( fd )
"""
    elif pull.startswith('dill'):
        code = """
def pull(path):
    import dill
    with open(path, 'rb') as fd:
        return dill.load( fd )
"""
    elif pull == 'json':
        code = """
def pull(path):
    import json
    with open(path, 'rb') as fd:
        return json.load(fd)
"""
    elif pull == 'numpy':
        code = """
def pull(path):
    import numpy
    with open(path, 'rb') as fd:
        return numpy.load(file=fd)

"""
    elif pull == 'numpy_text':
        code = """
def pull(path):
    import numpy
    with open(path, 'rb') as fd:
        return numpy.loadtxt(fname=fd)
"""
    else:
        if not (isinstance(pull, str)):
            raise Exception("pull must be None or a string")
        code = pull
    # return
    return code



def get_temporary_path(path):
    """
    Builds the path of a temporary file for writing a file atomically. The name is unique to the
    process and to every call, so writers can never write the same temporary file, even if the locks
    that normally keep them apart fail. The original file name stays at the end, because dump methods may
    depend on its extension.

    :Parameters:
        #. path (str): The file that is going to be written.

    :Returns:
        #. temporaryPath (str): A path in the same directory, which makes the final rename atomic.
    """
    # Only the end of the name is kept, so the extension and the kind suffix survive and the name stays short enough for the file system
    return os.path.join(os.path.dirname(path), '.pyreptmp_%i_%s_%s'%(os.getpid(), uuid.uuid4().hex[:8], os.path.basename(path)[-40:]))


def write_pickle_file(path, value, protocol):
    """
    Pickles a value into a file and makes sure it reaches the disk.

    :Parameters:
        #. path (str): The file to write.
        #. value (object): The value to pickle.
        #. protocol (int): The pickle protocol.
    """
    with open(path, 'wb') as fd:
        pickle.dump( value, fd, protocol=protocol )
        fd.flush()
        os.fsync(fd.fileno())


def get_file_signature(status):
    """
    Builds the signature that tells whether a file was replaced or changed.

    :Parameters:
        #. status (os.stat_result): The status of the file.

    :Returns:
        #. signature (tuple): The inode, the modification time in nanoseconds and the size. Files that pyrep writes are always replaced as a whole, so their inode changes with every save.
    """
    return (status.st_ino, status.st_mtime_ns, status.st_size)


def write_pickle_atomically(path, value, protocol):
    """
    Pickles a value into a file such that a crash or a kill leaves either the complete previous content or
    the complete new content, never a partial file. The value is written to a temporary file next to the
    destination and then moved over it in a single step.

    :Parameters:
        #. path (str): The file to write.
        #. value (object): The value to pickle.
        #. protocol (int): The pickle protocol.
    """
    tempPath = get_temporary_path(path)
    try:
        write_pickle_file(tempPath, value, protocol)
        os.replace(tempPath, path)
    except Exception:
        # A failed write must not leave a temporary file behind
        if os.path.isfile(tempPath):
            os.remove(tempPath)
        raise


def get_class_name(value):
    """
    Gets the name of the class of a value, which is what the class file of a repository file stores.
    A name is stored instead of the class itself because many classes, such as functions, cannot be pickled.

    :Parameters:
        #. value (object): Any value, None included.

    :Returns:
        #. name (None, str): The module and qualified class name, or None when the value is None.
    """
    if value is None:
        return None
    klass = value.__class__
    return '%s.%s'%(klass.__module__, klass.__qualname__)


def write_journal(journalPath, kind, data, protocol):
    """
    Writes a journal, the record of an operation that must be completed even if the process dies in the middle of it.
    Writing the journal is atomic, and it is the point from which the operation is completed instead of undone.
    Which function completes it is told by the kind, see Repository.recover_journal.

    :Parameters:
        #. journalPath (str): The journal file.
        #. kind (str): What the journal describes, such as 'file_moves' or 'rename_directory'.
        #. data (object): What is needed to complete it.
        #. protocol (int): The pickle protocol.
    """
    write_pickle_atomically(journalPath, {'kind': kind, 'data': data}, protocol)


def read_journal(journalPath):
    """
    Reads a journal.

    :Parameters:
        #. journalPath (str): The journal file.

    :Returns:
        #. kind (str): What the journal describes.
        #. data (object): What is needed to complete it.

    :Raises:
        #. Exception: If the file is not a journal.
    """
    with open(journalPath, 'rb') as fd:
        record = pickle.load(fd)
    if not (isinstance(record, dict) and set(record) == {'kind', 'data'}):
        raise Exception("'%s' is not a pyrep journal"%(journalPath,))
    return record['kind'], record['data']


def finish_file_moves(journalPath):
    """
    Completes the file moves that a journal of the kind 'file_moves' lists. The journal names temporary files and
    the names they must take in the same directory. Moving a temporary file that is already gone is skipped, so
    finishing is safe to repeat, which is what makes it safe to interrupt as well.

    :Parameters:
        #. journalPath (str): The journal file, which is removed once everything is moved.
    """
    kind, moves = read_journal(journalPath)
    if kind != 'file_moves':
        raise Exception("'%s' is a journal of the kind '%s', not of file moves"%(journalPath, kind))
    directory = os.path.dirname(journalPath)
    for tempName, finalName in moves:
        tempPath = os.path.join(directory, tempName)
        if os.path.exists(tempPath):
            os.replace(tempPath, os.path.join(directory, finalName))
    os.remove(journalPath)


def write_files_together(dumpFunc, path, value, pickled, protocol, journalPath):
    """
    Writes a data file together with the files that describe it, such that a crash or a failure leaves either
    all of them as they were or all of them new, never a mix. Every file is first written completely to a
    temporary file. Then a journal that lists the moves is written, which is the commit point. A crash before it
    leaves the old files, and the temporary files are leftovers. A crash after it is completed by
    whoever touches the file next, because the journal says what is left to move.

    :Parameters:
        #. dumpFunc (callable): The dump function of the data file, called as dumpFunc(path=..., value=...).
        #. path (str): The data file to write.
        #. value (object): The value to dump to the data file.
        #. pickled (list): Tuples of path and value of the files to pickle, such as the info and class files.
        #. protocol (int): The pickle protocol of the pickled files and of the journal.
        #. journalPath (str): Where to write the journal, in the directory of the data file.

    :Raises:
        #. Exception: If a write fails or the dump function does not create the file it was given.
    """
    prepared = []
    try:
        tempPath = get_temporary_path(path)
        prepared.append((tempPath, path))
        dumpFunc(path=tempPath, value=value)
        if not os.path.isfile(tempPath):
            raise Exception("the dump method did not create the file it was given")
        for pickledPath, pickledValue in pickled:
            tempPath = get_temporary_path(pickledPath)
            prepared.append((tempPath, pickledPath))
            write_pickle_file(tempPath, pickledValue, protocol)
        # The journal is the commit point
        write_journal(journalPath, 'file_moves', [(os.path.basename(t), os.path.basename(f)) for t, f in prepared], protocol)
    except Exception:
        # Nothing was committed, so the temporary files are only in the way
        for tempPath, _ in prepared:
            if os.path.isfile(tempPath):
                os.remove(tempPath)
        raise
    finish_file_moves(journalPath)


def copy_files_together(copies, journalPath, protocol, link=False):
    """
    Copies several files so that a crash leaves either all destinations as they were or all of them new.
    It works like write_files_together, with copies instead of dumps.

    :Parameters:
        #. copies (list): Tuples of the source and the destination path. All destinations are in the same directory.
        #. journalPath (str): Where to write the journal, in the directory of the destinations.
        #. protocol (int): The pickle protocol of the journal.
        #. link (boolean): Whether to make hard links instead of copies, which takes no time for any size.
           Files systems without hard links get copies.
    """
    prepared = []
    try:
        for source, destination in copies:
            tempPath = get_temporary_path(destination)
            prepared.append((tempPath, destination))
            if link:
                try:
                    os.link(source, tempPath)
                except OSError:
                    # This file system or this pair of directories cannot be linked
                    shutil.copyfile(source, tempPath)
            else:
                shutil.copyfile(source, tempPath)
        write_journal(journalPath, 'file_moves', [(os.path.basename(t), os.path.basename(f)) for t, f in prepared], protocol)
    except Exception:
        for tempPath, _ in prepared:
            if os.path.isfile(tempPath):
                os.remove(tempPath)
        raise
    finish_file_moves(journalPath)


def path_required(func):
    """
    Decorates the methods that only make sense once a repository is created or loaded. Called too early,
    they warn and return None.

    :Parameters:
        #. func (callable): The method to decorate.

    :Returns:
        #. wrapper (callable): The decorated method.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.path is None:
            warnings.warn('Must load (Repository.load_repository) or initialize (Repository.create_repository) the repository first !')
            return
        return func(self, *args, **kwargs)
    return wrapper


class InterpreterError(Exception):
    """
    Raised when the source code of a dump or pull method cannot be compiled or run.
    """

def my_exec(cmd, name, description):
    """
    Runs source code and returns the function it defines under the given name.

    :Parameters:
        #. cmd (str): The source code.
        #. name (str): The name of the function the code must define.
        #. description (str): What the code is for, used in the error message.

    :Returns:
        #. func (callable): The function defined by the code.

    :Raises:
        #. InterpreterError: If the code cannot be compiled, raises when run, or does not define the function.
    """
    try:
        namespace = {}
        exec(cmd, namespace)
        func = namespace[name]
    except SyntaxError as err:
        errorClass = err.__class__.__name__
        detail     = str(err.args[0]) if len(err.args) else ''
        lineNumber = err.lineno
    except Exception as err:
        errorClass = err.__class__.__name__
        detail     = str(err)
        lineNumber = traceback.extract_tb(sys.exc_info()[2])[-1][1]
    else:
        return func
    raise InterpreterError("%s at line %d of %s: %s" % (errorClass, lineNumber, description, detail))



def copy_tree(src, dst, srcDirDict,
              filAttr=('.%s_pyrepfileinfo','.%s_pyrepfileclass'),
              dirAttr=('.pyrepdirinfo','.pyreprepo')):
    """
    Copies the tracked part of a repository directory tree from a source to a destination.
    It does not use the distutils copy_tree, which fails when the destination was removed earlier in the same session.

    :Parameters:
        #. src (str): The source directory.
        #. dst (str): The destination directory, created when missing.
        #. srcDirDict (dict): Single key dictionary of the source directory name to the list of
           files and directories tracked in it.
        #. filAttr (tuple): Name patterns of the files that accompany every tracked file, where %s is the file name.
        #. dirAttr (tuple): Names of the files that accompany every directory.

    :Returns:
        #. files (list): The destination paths that were copied.
    """
    files = []
    if not (os.path.isdir(src)):
        raise Exception("given source directory '%s' does not exist"%src)
    src = src.rstrip(os.sep)
    dst = dst.rstrip(os.sep)
    if not (src!=dst):
        raise Exception("source and destination directories are given the same '%s'"%src)
    if not (isinstance(srcDirDict, dict)):
        raise Exception("source directory dictionary must be a dictionary ")
    if not (len(srcDirDict) == 1):
        raise Exception("source directory dictionary must be a dictionary of length 1")
    dirName = list(srcDirDict)[0]
    dirList = srcDirDict[dirName]
    srcDirName = os.path.basename(src)
    if not (dirName == srcDirName):
        raise Exception("source directory dictionary single key must be the source directory name '%s' but '%s' is found"%(srcDirName, dirName))
    # create destination directory
    if not os.path.isdir(dst):
        os.makedirs(dst, exist_ok=True)
        for attr in dirAttr:
            srcp = os.path.join(src, attr)
            if os.path.isfile(srcp):
                dstp = os.path.join(dst, attr)
                shutil.copyfile(srcp, dstp)
    # copy files
    for f in dirList:
        if isinstance(f, str):
            srcp = os.path.join(src, f)
            dstp = os.path.join(dst, f)
            shutil.copyfile(srcp, dstp)
            for attr in filAttr:
                srcp = os.path.join(src, attr%f)
                if os.path.isfile(srcp):
                    dstp = os.path.join(dst, attr%f)
                    shutil.copyfile(srcp, dstp)
            files.append(dstp)
    # copy directories
    for d in dirList:
        if isinstance(d, dict):
            if not (len(d) == 1):
                raise Exception('Condition not met: len(d) == 1')
            fname = list(d)[0]
            src1  = os.path.join(src,fname)
            dst1  = os.path.join(dst,fname)
            files.extend( copy_tree(src=src1, dst=dst1, srcDirDict=d, filAttr=filAttr, dirAttr=dirAttr) )
    # return files
    return files




class Repository:
    """
    This is a pythonic way to organize dumping and pulling python objects
    or any type of files to a folder or directory that we call repository.
    Any directory can be a repository, it suffices to initialize a Repository
    instance in a directory to start dumping and pulling object into it.
    Any directory that has .pyreprepo pickle file in it is theoretically a
    pyrep Repository. Repository is thread and process safe. Multiple processes
    and threads can access, create, dump and pull into the repository.

    :Parameters:
        #. path (None, string): This is used to load a repository instance.\n
           If None, Repository is initialized but not assigned to any directory.\n
           If Path is given then repository will be loaded from path if
           existing.
        #. pickleProtocol (int): Pickle protocol. Default value is 4, which every
           python 3.4 or newer reads. pickle.HIGHEST_PROTOCOL or -1 uses the
           highest protocol of the running python, which older pythons may not read.
        #. timeout (number): The seconds to wait for a lock on each attempt. A lock that
           stays taken is tried four times with half a second between attempts,
           so a failure takes up to four times this plus 1.5 seconds.
        #. password (None, string): the locker password to manage the
           repository access. If None, default password is given
        #. removeTemporaryFiles (boolean): Whether loading the repository at *path*
           removes the temporary files that crashed writes left behind. Only files
           untouched for TEMPORARY_FILES_MAX_AGE seconds are removed.
        #. removeOrphanFiles (boolean): Whether loading the repository at *path*
           removes the files of the repository that its index no longer lists,
           which crashed operations leave behind. Only files untouched for
           ORPHAN_FILES_MAX_AGE seconds are removed.
    """
    DEBUG_PRINT_FAILED_TRIALS = False#True

    # Seconds a temporary file must be untouched before loading a repository removes it, so a write in progress is never hit
    TEMPORARY_FILES_MAX_AGE = 3600

    # Seconds the files that the index does not list must be untouched before loading a repository removes them
    ORPHAN_FILES_MAX_AGE = 3600

    def __init__(self, path=None, pickleProtocol=4, timeout=10, password=None, removeTemporaryFiles=True, removeOrphanFiles=True):
        self.__repoLock  = '.pyreplock'
        self.__repoFile  = '.pyreprepo'
        self.__dirInfo   = '.pyrepdirinfo'
        self.__dirLock   = '.pyrepdirlock'
        self.__fileInfo  = '.%s_pyrepfileinfo'  # %s replaces file name
        self.__fileClass = '.%s_pyrepfileclass'  # %s replaces file name
        self.__fileLock  = '.%s_pyrepfilelock'  # %s replaces file name
        self.__fileJournal = '.%s_pyrepjournal'  # %s replaces file name
        self.__repoJournal = '.pyrepjournal'
        self.__isDefaultPassword = password is None
        if password is None:
            password = "pyrep_repository_b@11a"
        if not (isinstance(password, str)):
            raise Exception("password must be None or a string")
        self.__password = password
        self.__locker   = None
        # set default protocols
        if not (isinstance(pickleProtocol, int)):
            raise Exception("pickleProtocol must be integer")
        if not (pickleProtocol>=-1):
            raise Exception("pickleProtocol must be >=-1")
        self._DEFAULT_PICKLE_PROTOCOL = pickleProtocol
        # initialize repository
        self.reset()
        # set timeout
        self.timeout = timeout
        # if path is not None, load existing repository
        if path is not None:
            if not (self.is_repository(path)):
                raise Exception("given path is not a repository. use create_repository or give a valid repository path")
            self.load_repository(path, removeTemporaryFiles=removeTemporaryFiles, removeOrphanFiles=removeOrphanFiles)

    def __str__(self):
        if self.__path is None:
            return ""
        string = os.path.normpath(self.__path)
        reprSt = self.get_repository_state()
        # walk files
        leftAdjust = "  "
        for fdict in reprSt:
            fdname = list(fdict)[0]
            if fdname == '':
                continue
            if fdict[fdname].get('pyrepfileinfo', False):
                string += "\n"
                string += leftAdjust
                string += os.path.basename(fdname)
            elif fdict[fdname].get('pyrepdirinfo', False):
                splitPath = fdname.split(os.sep)
                leftAdjust = ''.join(['  '*(len(item)>0) for item in splitPath])
                string += "\n"
                string += leftAdjust
                string += os.sep+str(splitPath[-1])
            else:
                raise Exception('Not sure what to do next. Please report issue')
        return string

    def __getstate__(self):
        state = {}
        state.update( self.__dict__ )
        state['_Repository__locker'] = None
        # a user given password is a secret and must not be written to the pickle
        if not self.__isDefaultPassword:
            state['_Repository__password'] = None
        return state

    def __setstate__(self, state):
        path          = state['_Repository__path']
        needsPassword = not state['_Repository__isDefaultPassword'] and state['_Repository__password'] is None
        state['_Repository__locker'] = None
        # set state
        self.__dict__ = state
        if path is not None and not needsPassword:
            self.__start_locker(os.path.join(path, self.__repoLock))
        if needsPassword:
            self.reset()
            warnings.warn("A custom repository password is not stored in a pickle. Use Repository(path, password=...) to reopen the repository.")


    def __repr__(self):
        repr = "pyrep "+self.__class__.__name__+" (Version "+str(self.__repo['pyrep_version'])+")"
        if self.__path is None:
            return repr
        ndirs, nfiles = self.get_stats()
        repr += " @%s [%i directories] [%i files] "%(self.__path, ndirs, nfiles)
        return repr

    def __sync_files(self, repoPath, dirs):
        errors  = []
        synched = []
        def _walk_dir(relPath, relDirList, relSynchedList):
            if not os.path.isdir(os.path.join(repoPath, relPath)):
                errors.append("Repository directory '%s' not found on disk"%relPath)
            else:
                for k in relDirList:
                    if isinstance(k, dict):
                        if len(k)!=1:
                            errors.append("Repository directory found in '%s' info dict length is not 1"%relPath)
                            continue
                        dn = list(k)[0]
                        if not isinstance(dn, str):
                            errors.append("Repository directory found in '%s' info dict key is not a string"%relPath)
                            continue
                        if not len(dn):
                            errors.append("Repository directory found in '%s' info dict key is an empty string"%relPath)
                            continue
                        if not os.path.isfile(os.path.join(repoPath, relPath, self.__dirInfo)):
                            errors.append("Repository directory info file '%s' not found on disk"%os.path.join(repoPath, relPath, self.__dirInfo))
                            continue
                        rp = os.path.join(repoPath, relPath, dn)
                        rsd = {dn:[]}
                        relSynchedList.append(rsd)
                        _walk_dir(relPath=rp, relDirList=k[dn], relSynchedList=rsd[dn])
                    elif isinstance(k, str):
                        relFilePath = os.path.join(repoPath, relPath, k)
                        relInfoPath = os.path.join(repoPath, relPath, self.__fileInfo%k)
                        if not os.path.isfile(relFilePath):
                            errors.append("Repository file '%s' not found on disk"%relFilePath)
                            continue
                        elif not os.path.isfile(relInfoPath):
                            errors.append("Repository file info file '%s' not found on disk"%relFilePath)
                            continue
                        relSynchedList.append(k)
                    else:
                        errors.append("Repository file found in '%s' info dict key is not a string"%relPath)
                        continue
        # call recursive _walk_dir
        _walk_dir(relPath='', relDirList=dirs, relSynchedList=synched)
        return synched, errors


    @property
    def len(self):
        """The number of directories and files tracked in the repository, as a dictionary."""
        ndirs, nfiles = self.get_stats()
        return {'number_of_directories':ndirs, 'number_of_files':nfiles}

    @property
    def locker(self):
        """The locker this instance uses to coordinate access to the repository."""
        return self.__locker

    def __save_dirinfo(self, description, dirInfoPath, create=False):
        # create main directory info file
        oldInfo = None
        if description is None and os.path.isfile(dirInfoPath):
            with open(dirInfoPath, 'rb') as fd:
                oldInfo = pickle.load(fd)
            if self.__repo['repository_unique_name'] != oldInfo['repository_unique_name']:
                description = ''
        if description is None and create:
            description = ''
        if description is not None:
            if os.path.isfile(dirInfoPath):
                if oldInfo is None:
                    with open(dirInfoPath, 'rb') as fd:
                        oldInfo = pickle.load(fd)
                if self.__repo['repository_unique_name'] != oldInfo['repository_unique_name']:
                    createTime = lastUpdateTime = time.time()
                else:
                    createTime     = oldInfo['create_utctime']
                    lastUpdateTime = time.time()
            else:
                createTime = lastUpdateTime = time.time()
            info = {'repository_unique_name':self.__repo['repository_unique_name'],
                    'create_utctime':createTime,
                    'last_update_utctime':lastUpdateTime,
                    'description':description}
            write_pickle_atomically(dirInfoPath, info, self._DEFAULT_PICKLE_PROTOCOL)

    def __clean_before_after(self, stateBefore, stateAfter, keepNoneEmptyDirectory=True):
        """clean repository given before and after states"""
        # prepare after for faster search
        errors    = []
        afterDict = {}
        [afterDict.setdefault(list(aitem)[0],[]).append(aitem) for aitem in stateAfter]
        # loop before
        for bitem in reversed(stateBefore):
            relaPath = list(bitem)[0]
            basename = os.path.basename(relaPath)
            btype    = bitem[relaPath]['type']
            alist    = afterDict.get(relaPath, [])
            aitem    = [a for a in alist if a[relaPath]['type']==btype]
            if len(aitem)>1:
                errors.append("Multiple '%s' of type '%s' where found in '%s', this should never had happened. Please report issue"%(basename,btype,relaPath))
                continue
            if not len(aitem):
                removeDirs  = []
                removeFiles = []
                if btype == 'dir':
                    if not len(relaPath):
                        errors.append("Removing main repository directory is not allowed")
                        continue
                    removeDirs.append(os.path.join(self.__path,relaPath))
                    removeFiles.append(os.path.join(self.__path,relaPath,self.__dirInfo))
                    removeFiles.append(os.path.join(self.__path,relaPath,self.__dirLock))
                elif btype == 'file':
                    parentPath = os.path.join(self.__path,os.path.dirname(relaPath))
                    removeFiles.append(os.path.join(self.__path,relaPath))
                    removeFiles.append(os.path.join(parentPath,self.__fileInfo%basename))
                    removeFiles.append(os.path.join(parentPath,self.__fileClass%basename))
                    removeFiles.append(os.path.join(parentPath,self.__fileLock%basename))
                # remove files
                for fpath in removeFiles:
                    if os.path.isfile(fpath):
                        try:
                            os.remove(fpath)
                        except Exception as err:
                            errors.append("Unable to clean file '%s' (%s)"%(fpath, str(err)))
                # remove directories
                for dpath in removeDirs:
                    if os.path.isdir(dpath):
                        if keepNoneEmptyDirectory or not len(os.listdir(dpath)):
                            try:
                                shutil.rmtree(dpath)
                            except Exception as err:
                                errors.append("Unable to clean directory '%s' (%s)"%(dpath, str(err)))
        # return result and errors list
        return len(errors)==0, errors


    def __get_repository_parent_directory(self, relativePath):
        relativePath = self.to_repo_relative_path(path=relativePath, split=False)
        if relativePath == '':
            return None
        parentPath = os.path.dirname(relativePath)
        return self.__get_repository_directory(relativePath=parentPath)

    def __get_repository_directory(self, relativePath):
        cDir = self.__repo['walk_repo']
        splitted = self.to_repo_relative_path(path=relativePath, split=True)
        if splitted == ['']:
            return cDir
        for dirname in splitted:
            dList = [d for d in cDir if isinstance(d, dict)]
            if not len(dList):
                cDir = None
                break
            cDict = [d for d in dList if dirname in d]
            if not len(cDict):
                cDir = None
                break
            cDir = cDict[0][dirname]
        # return
        return cDir

    def __save_repository_pickle_file(self, lockFirst=False, raiseError=True):
        # create and acquire lock
        error = None
        if lockFirst:
            acquired, lockId = self.__acquire_lock(self.__path)
            # check if acquired.
            if not acquired:
                error = "code %s. Unable to acquire the repository lock. You may try again!"%(lockId,)
                if raiseError:
                    raise Exception(error)
                return False,error
        try:
            repoInfoPath = os.path.join(self.__path, self.__repoFile)
            self.__repo["last_update_utctime"] = time.time()
            write_pickle_atomically(repoInfoPath, self.__repo, self._DEFAULT_PICKLE_PROTOCOL)
            self.__indexSignature = get_file_signature(os.stat(repoInfoPath))
        except Exception as err:
            error = "Unable to save repository (%s)"%str(err)
        # release lock
        if lockFirst:
            self.__locker.release_lock(lockId)
        # return
        if error is not None and raiseError:
            raise Exception(error)
        return error is None, error

    def __load_repository_pickle_file(self, repoPath, track=True):
        try:
            fd = open(repoPath, 'rb')
        except Exception as err:
            raise Exception("Unable to open repository file(%s)"%str(err)) from err
        # The signature comes from the open file, so it describes exactly the content that is read
        signature = get_file_signature(os.fstat(fd.fileno()))
        # read
        try:
            repo = pickle.load( fd )
        except Exception as err:
            fd.close()
            raise Exception("Unable to load pickle repository (%s)"%str(err) ) from err
        else:
            fd.close()
        # check if it's a pyreprepo instance
        if not (isinstance(repo, dict)):
            raise Exception("pyrep repo must be a dictionary")
        if not ("create_utctime" in repo):
            raise Exception("'create_utctime' must be a key in pyrep repo dict")
        if not ("last_update_utctime" in repo):
            raise Exception("'last_update_utctime' must be a key in pyrep repo dict")
        if not ("pyrep_version" in repo):
            raise Exception("'pyrep_version' must be a key in pyrep repo dict")
        if not ("walk_repo" in repo):
            raise Exception("'walk_repo' must be a key in pyrep repo dict")
        if not (isinstance(repo['walk_repo'], list)):
            raise Exception("pyrep info 'walk_repo' key value must be a list")
        if track:
            self.__indexSignature = signature
        # return
        return repo

    def __load_repository(self, path, verbose=True, safeMode=True):
        # try to open
        if path.strip() in ('','.'):
            path = os.getcwd()
        repoPath = os.path.realpath( os.path.expanduser(path) )
        if os.sep=='\\':
            repoPath = re.sub(r'([\\])\1+', r'\1', repoPath).replace('\\','\\\\')
        if not self.is_repository(repoPath):
            raise Exception("No repository found in '%s'"%str(repoPath))
        # update locker serverFile and start
        serverFile = os.path.join(repoPath, self.__repoLock)
        self.__start_locker(serverFile)
        # acquire lock
        if safeMode:
            acquired, lockId = self.__locker.acquire_lock(path=repoPath, timeout=self.timeout)
            # Code 2 = locker is neither server nor client — stale broken locker in FACTORY cache.
            # Regenerate a fresh ServerLocker whose __init__ picks up the current IP naturally.
            if not acquired and lockId == 2:
                self.__start_locker(serverFile, regenerate=True)
                acquired, lockId = self.__locker.acquire_lock(path=repoPath, timeout=self.timeout)
            # check if acquired.
            if not acquired:
                raise Exception("code %s. Unable to acquire the lock when calling 'load_repository'"%(lockId,))
        # load repository
        error = None
        try:
            repo = self.__load_repository_pickle_file( os.path.join(repoPath, self.__repoFile) )
            # get paths dict
            repoFiles, errors = self.__sync_files(repoPath=repoPath, dirs=repo['walk_repo'])
            if len(errors) and verbose:
                warnings.warn("\n".join(errors))
            self.__path = repoPath
            self.__repo['repository_unique_name'] = repo['repository_unique_name']
            self.__repo['repository_information'] = repo['repository_information']
            self.__repo['create_utctime']         = repo['create_utctime']
            self.__repo['last_update_utctime']    = repo['last_update_utctime']
            self.__repo['walk_repo']              = repoFiles
        except Exception as err:
            error = str(err)
        # release lock
        if safeMode:
            self.__locker.release_lock(lockId)
        # check for any error
        if error is not None:
            raise Exception(error)

    @property
    def info(self):
        """Get repository information"""
        return self.__repo['repository_information']

    @property
    def path(self):
        """The repository instance path which points to the directory where
        .pyreprepo is."""
        return self.__path

    @property
    def uniqueName(self):
        """Get repository unique name as generated when repository was created"""
        return self.__repo['repository_unique_name']

    def __start_locker(self, serverFile, regenerate=False):
        """
        Gets and starts the locker shared by all the instances of this process that work on the same repository
        and registers this instance as one of its users.
        """
        locker = FACTORY(key=serverFile, password=self.__password, serverFile=serverFile, autoconnect=False, regenerate=regenerate)
        locker.start()
        with LOCKER_USERS_MUTEX:
            LOCKER_USERS.setdefault(serverFile, weakref.WeakSet()).add(self)
        self.__locker = locker
        return locker

    def __replace_locker(self, brokenLocker):
        """
        Replaces a locker whose server is gone. The first call elects this process as the new server,
        instances and threads that follow adopt the locker the first one made.
        """
        with LOCKER_USERS_MUTEX:
            if self.__locker is not brokenLocker:
                return
            serverFile = os.path.join(self.__path, self.__repoLock)
            cached     = FACTORY(key=serverFile, password=self.__password, serverFile=serverFile, autoconnect=False)
            self.__start_locker(serverFile, regenerate=cached is brokenLocker)

    def __acquire_lock(self, path):
        """
        Acquires a lock and, when the lock server is gone, takes its place and tries once more.
        Codes 1 and 2 of the locker mean that there is no server to talk to.
        """
        locker = self.__locker
        acquired, lockId = locker.acquire_lock(path=path, timeout=self.timeout)
        if not acquired and lockId in (1, 2):
            self.__replace_locker(locker)
            acquired, lockId = self.__locker.acquire_lock(path=path, timeout=self.timeout)
        if acquired and path == self.__path:
            # Whoever holds the repository lock first completes what a crash interrupted
            try:
                self.__recover_repository_journal()
            except Exception as err:
                self.__locker.release_lock(lockId)
                return False, "unable to complete an interrupted operation (%s)"%(err,)
        return acquired, lockId

    def __remove_files(self, paths):
        """
        Removes files that are not needed anymore, once the index no longer lists them. A file that cannot be
        removed is an orphan and does no harm, so failures are returned and never raised.
        """
        failed = []
        for path in paths:
            try:
                if os.path.isfile(path):
                    os.remove(path)
            except OSError as err:
                failed.append("%s (%s)"%(path, err))
        return failed

    def __resync_index(self):
        """
        Reads the tracked list from the saved index again, after a change that could not be saved.
        """
        try:
            self.__repo['walk_repo'] = self.__load_repository_pickle_file(os.path.join(self.__path, self.__repoFile))['walk_repo']
        except Exception:
            # The next operation reloads it anyway
            pass

    def __recover_journal(self, journalPath):
        """
        Completes the operation a journal describes. Every kind of journal has the function that completes it in the
        table below, so a new kind of journal is one new function and one new line. The lock that protects the
        journal's scope must be held: the file lock for a journal next to a data file, the repository lock for
        the journal in the repository directory.
        """
        kind, data = read_journal(journalPath)
        completers = {'file_moves': lambda: finish_file_moves(journalPath),
                      'rename_directory': lambda: self.__finish_directory_rename(journalPath, data)}
        if kind not in completers:
            raise Exception("'%s' is a journal of the unknown kind '%s'"%(journalPath, kind))
        completers[kind]()

    def __recover_commit(self, realPath):
        """
        Completes a commit that a crash interrupted for a data file, if there is one. The file lock must be held.
        """
        journalPath = os.path.join(os.path.dirname(realPath), self.__fileJournal%os.path.basename(realPath))
        if os.path.isfile(journalPath):
            self.__recover_journal(journalPath)

    def __recover_repository_journal(self):
        """
        Completes the operation that a crash interrupted in the repository, if there is one. The repository lock must be held.
        """
        journalPath = os.path.join(self.__path, self.__repoJournal)
        if os.path.isfile(journalPath):
            self.__recover_journal(journalPath)

    def __finish_directory_rename(self, journalPath, data):
        """
        Completes a directory rename that a crash interrupted. What is on disk decides: when the old directory is
        still there the directory was never renamed and there is nothing to complete, when only the new one is
        there the index must name it as well. The repository lock must be held.
        """
        parent, old, new = data['parent'], data['old'], data['new']
        oldExists = os.path.isdir(os.path.join(self.__path, parent, old))
        newExists = os.path.isdir(os.path.join(self.__path, parent, new))
        if newExists and not oldExists:
            self.__repo['walk_repo'] = self.__load_repository_pickle_file(os.path.join(self.__path, self.__repoFile))['walk_repo']
            parentList = self.__get_repository_directory(parent)
            if parentList is not None:
                oldEntries = [entry for entry in parentList if isinstance(entry, dict) and old in entry]
                newEntries = [entry for entry in parentList if isinstance(entry, dict) and new in entry]
                if len(oldEntries) == 1 and len(newEntries) == 0:
                    oldEntries[0][new] = oldEntries[0].pop(old)
                    saved, error = self.__save_repository_pickle_file(lockFirst=False, raiseError=False)
                    if not saved:
                        raise Exception(error)
        elif not (oldExists and not newExists):
            warnings.warn("The interrupted renaming of '%s' to '%s' cannot be decided because both of them or none of them exist, it is left as it is"%(os.path.join(parent, old), os.path.join(parent, new)))
        os.remove(journalPath)

    def __acquire_file_lock(self, realPath):
        """
        Acquires the lock of a data file and completes the commit that a crash may have interrupted for it,
        so that whatever the caller reads or replaces next is a whole state of the file.
        Failing to complete the commit counts as not acquiring, and the lock is given back.
        """
        acquired, lockId = self.__acquire_lock(realPath)
        if acquired:
            try:
                self.__recover_commit(realPath)
            except Exception as err:
                self.__locker.release_lock(lockId)
                return False, "unable to complete an interrupted commit (%s)"%(err,)
        return acquired, lockId

    def close(self):
        """
        Closes this instance. The locker is stopped only when no other instance of this process still uses it.
        """
        if self.__locker is None:
            return
        serverFile = os.path.join(self.__path, self.__repoLock)
        with LOCKER_USERS_MUTEX:
            users = LOCKER_USERS.get(serverFile, weakref.WeakSet())
            users.discard(self)
            isLastUser = len(users) == 0
        if isLastUser:
            self.__locker.stop()

    def get_stats(self):
        """
        Get repository descriptive stats

        :Returns:
            #. numberOfDirectories (integer): Number of diretories in repository
            #. numberOfFiles (integer): Number of files in repository
        """
        if self.__path is None:
            return 0,0
        nfiles = 0
        ndirs  = 0
        for fdict in self.get_repository_state():
            fdname = list(fdict)[0]
            if fdname == '':
                continue
            if fdict[fdname].get('pyrepfileinfo', False):
                nfiles += 1
            elif fdict[fdname].get('pyrepdirinfo', False):
                ndirs += 1
            else:
                # this could happen with asynchronous calls upon the repository
                # or if the file or directory are not registered in the repository
                warnings.warn("'%s' is neither a repository file nor a directory. This can happen when accessing the repository asynchronously."%(fdname))
                continue
        return ndirs,nfiles


    def reset(self):
        """Reset repository instance.
        """
        self.__path   = None
        self.__locker = None
        # Signature of the index file as this instance loaded or saved it, used to notice changes made by others
        self.__indexSignature = None
        self.__repo   = {'repository_unique_name': str(uuid.uuid1()),
                         'create_utctime': time.time(),
                         'last_update_utctime': None,
                         'pyrep_version': str(__version__),
                         'repository_information': '',
                         'walk_repo': []}


    def is_repository(self, path):
        """
        Check if there is a Repository in path.

        :Parameters:
            #. path (string): The real path of the directory where to check if
               there is a repository.

        :Returns:
            #. result (boolean): Whether it's a repository or not.
        """
        if path.strip() in ('','.'):
            path = os.getcwd()
        repoPath = os.path.realpath( os.path.expanduser(path) )
        if os.path.isfile( os.path.join(repoPath,self.__repoFile) ):
            return True
        else:
            return False


    def load_repository(self, path, verbose=True, ntrials=3, safeMode=True, removeTemporaryFiles=True, removeOrphanFiles=True):
        """
        Load repository from a directory path and update the current instance.
        First, new repository still will be loaded. If failed, then old
        style repository load will be tried.

        :Parameters:
            #. path (string): The path of the directory from where to load
               the repository from. If '.' or an empty string is passed,
               the current working directory will be used.
            #. verbose (boolean): Whether to be verbose about abnormalities
            #. ntrials (int): The maximum number of attempts of the operation once its locks are held.
               Only an error that can pass by itself, such as a busy or interrupted call of the file
               system, is attempted again, after a pause that doubles with every attempt. Any other
               error fails at once, which also keeps your own dump and pull methods from running
               again after they failed. The message of a failure lists the error of every attempt.
            #. safeMode (boolean): loading repository can be done without
               acquiring from multiple processes. Not acquiring the lock
               can be unsafe if another process is altering the repository
            #. removeTemporaryFiles (boolean): Whether to remove the temporary files
               that crashed writes left behind. Only files untouched for
               TEMPORARY_FILES_MAX_AGE seconds are removed, so a write in progress
               in another process is never hit. A failure to remove them only warns.
            #. removeOrphanFiles (boolean): Whether to remove the files of the
               repository that the index no longer lists, which crashed operations
               leave behind. Only files untouched for ORPHAN_FILES_MAX_AGE seconds
               are removed, and only files that carry the info or class file that pyrep
               writes, so files of your own are never touched. A failure to remove them
               only warns.

        :Returns:
             #. repository (pyrep.Repository): returns self repository with loaded data.
        """
        if not (isinstance(safeMode, bool)):
            raise Exception("safeMode must be boolean")
        if not (isinstance(ntrials, int)):
            raise Exception("ntrials must be integer")
        if not (ntrials>0):
            raise Exception("ntrials must be >0")
        repo = None
        attempts = []
        for _trial in range(ntrials):
            try:
                self.__load_repository(path=path, verbose=True, safeMode=safeMode)
            except Exception as err1:
                error = "Unable to load repository (%s)"%(err1, )
                attempts.append(error)
                error = describe_attempts(attempts)
                if not should_retry(err1, _trial, ntrials):
                    break
            else:
                error = None
                repo  = self
                break
        # check and return
        if error is not None:
            raise Exception(error)
        self.__complete_repository_journal()
        if removeTemporaryFiles:
            try:
                self.remove_temporary_files(olderThan=self.TEMPORARY_FILES_MAX_AGE)
            except Exception as err:
                if verbose:
                    warnings.warn("Unable to remove the temporary files of '%s' (%s)"%(self.__path, err))
        if removeOrphanFiles:
            try:
                self.remove_orphan_files(olderThan=self.ORPHAN_FILES_MAX_AGE)
            except Exception as err:
                if verbose:
                    warnings.warn("Unable to remove the orphan files of '%s' (%s)"%(self.__path, err))
        return repo

    @path_required
    def __refresh_if_stale(self):
        """
        Reloads the tracked list when another instance or process saved the index after this instance read it.
        It is only called after something was not found, so that looking up a known name never costs a lock.
        It runs outside of every lock, which is why it takes the repository lock itself.
        """
        if self.__path is None:
            return False
        try:
            current = get_file_signature(os.stat(os.path.join(self.__path, self.__repoFile)))
        except OSError:
            return False
        if current == self.__indexSignature:
            return False
        return self.refresh_repository(raiseError=False)[0]

    def __get_directory_or_refresh(self, relativePath, parent=False):
        """
        Gets a tracked directory, or its parent, and looks again after reloading the list when it is not found
        and the index changed since this instance read it.
        """
        getter = self.__get_repository_parent_directory if parent else self.__get_repository_directory
        dirList = getter(relativePath)
        if dirList is None and self.__refresh_if_stale():
            dirList = getter(relativePath)
        return dirList

    def refresh_repository(self, raiseError=True):
        """
        Reloads the tracked files and directories from disk. An instance keeps the list it loaded or saved
        last. Looking up a name that is not in that list reloads it by itself when the index changed, so pulling or
        asking about a file that another instance added just works. Listings and names that others removed only
        change after a refresh.

        :Parameters:
            #. raiseError (boolean): Whether to raise encountered error instead
               of returning failure.

        :Returns:
            #. success (boolean): Whether refreshing was successful.
            #. message (None, str): The reason of the failure, None when it succeeded.
        """
        if not isinstance(raiseError, bool):
            raise Exception("raiseError must be boolean")
        acquired, repoLockId = self.__acquire_lock(self.__path)
        if not acquired:
            error = "code %s. Unable to acquire the repository lock when refreshing. You may try again!"%(repoLockId,)
            if raiseError:
                raise Exception(error)
            return False, error
        error = None
        try:
            repo = self.__load_repository_pickle_file(os.path.join(self.__path, self.__repoFile))
            self.__repo['walk_repo'] = repo['walk_repo']
        except Exception as err:
            error = str(err)
        self.__locker.release_lock(repoLockId)
        if error is not None and raiseError:
            raise Exception(error)
        return error is None, error

    @path_required
    def remove_temporary_files(self, olderThan=3600):
        """
        Completes the commits that crashed writes interrupted, then removes the temporary files that crashed writes
        left behind anywhere in the repository directory, also in directories that a crashed add_directory created
        but did not register.
        Temporary files are named after the process that wrote them and are never reused, so nothing else cleans them.

        :Parameters:
            #. olderThan (int, float): Only temporary files not modified for this many seconds are removed,
               because a younger one can belong to a write in progress.

        :Returns:
            #. removed (list): The relative paths of the removed files.
        """
        if not (isinstance(olderThan, (int, float)) and olderThan >= 0):
            raise Exception("olderThan must be a number >=0")
        removed = []
        now     = time.time()
        walked  = list(os.walk(self.__path))
        # Commits that a crash interrupted are completed first, because their temporary files are not leftovers
        journalSuffix = self.__fileJournal[3:]
        for realDir, _, names in walked:
            for name in names:
                # A journal that is still a temporary file was never committed, so it must not be completed
                if name.startswith('.') and not name.startswith('.pyreptmp_') and name.endswith(journalSuffix):
                    acquired, lockId = self.__acquire_file_lock(os.path.join(realDir, name[1:-len(journalSuffix)]))
                    if acquired:
                        self.__locker.release_lock(lockId)
                    else:
                        # A writer that is alive holds the lock and finishes its own commit
                        warnings.warn("Unable to complete the interrupted commit of '%s' (%s)"%(os.path.join(realDir, name), lockId))
        for realDir, _, names in os.walk(self.__path):
            for name in names:
                if not name.startswith('.pyreptmp_'):
                    continue
                realPath = os.path.join(realDir, name)
                try:
                    if now - os.path.getmtime(realPath) >= olderThan:
                        os.remove(realPath)
                        removed.append(os.path.relpath(realPath, self.__path))
                except OSError:
                    # Another process may have finished or removed it in the meantime
                    pass
        return removed

    def __complete_repository_journal(self):
        """
        Completes the operation that a crash interrupted in the repository, if there is one. Taking the repository
        lock does it, and the tracked list is read again while the lock is still held, so that no writer is
        working with the old list. Methods that only take the lock of a file call this first, because that lock
        does not complete it.
        """
        if os.path.isfile(os.path.join(self.__path, self.__repoJournal)):
            acquired, lockId = self.__acquire_lock(self.__path)
            if acquired:
                try:
                    self.__repo['walk_repo'] = self.__load_repository_pickle_file(os.path.join(self.__path, self.__repoFile))['walk_repo']
                finally:
                    self.__locker.release_lock(lockId)

    def __find_orphans(self, olderThan):
        """
        Lists the groups of files that the index does not list and that carry the info or the class file that pyrep
        writes for a data file. A group is the data file, when it is still there, and its info and class files, and
        only a group whose files are all older than the limit is listed. The index is read from disk.
        """
        # Only reads the index, so this instance must not take it as its own view
        walkRepo = self.__load_repository_pickle_file(os.path.join(self.__path, self.__repoFile), track=False)['walk_repo']
        tracked  = {}

        def collect(relativeDir, entries):
            tracked[relativeDir] = set(entry for entry in entries if isinstance(entry, str))
            for entry in entries:
                if isinstance(entry, dict):
                    for name, children in entry.items():
                        collect(os.path.join(relativeDir, name), children)

        collect('', walkRepo)
        infoSuffix, classSuffix = self.__fileInfo[3:], self.__fileClass[3:]
        now, groups = time.time(), []
        for realDir, _, names in os.walk(self.__path):
            relativeDir = os.path.relpath(realDir, self.__path)
            trackedNames = tracked.get('' if relativeDir == '.' else relativeDir, set())
            pieces = {}
            for name in names:
                if name.startswith('.') and not name.startswith('.pyreptmp_'):
                    for suffix in (infoSuffix, classSuffix):
                        if name.endswith(suffix) and len(name) > len(suffix) + 1:
                            dataName = name[1:-len(suffix)]
                            if dataName not in trackedNames:
                                pieces.setdefault(dataName, []).append(name)
            for dataName, found in pieces.items():
                group = found + ([dataName] if dataName in names else [])
                paths = [os.path.join(realDir, name) for name in group]
                try:
                    if all(now - os.path.getmtime(path) >= olderThan for path in paths):
                        groups.append(paths)
                except OSError:
                    # Gone in the meantime
                    pass
        return groups

    @path_required
    def remove_orphan_files(self, olderThan=3600):
        """
        Removes the files that crashed operations left behind and that the index no longer lists, such as the old
        names after a rename that completed or the new ones after a rename that did not. Only files that carry
        the info or the class file that pyrep writes are removed, and only when all of them were not modified for
        the given time, so files of your own and writes in progress are never touched. The repository lock is taken
        only when there is something to remove, because no writer can register a file while it is held.

        :Parameters:
            #. olderThan (int, float): How many seconds the files must be untouched.

        :Returns:
            #. removed (list): The relative paths of the removed files.

        :Raises:
            #. Exception: If olderThan is not a number >=0 or the repository lock cannot be acquired.
        """
        if not (isinstance(olderThan, (int, float)) and olderThan >= 0):
            raise Exception("olderThan must be a number >=0")
        if not len(self.__find_orphans(olderThan)):
            return []
        acquired, lockId = self.__acquire_lock(self.__path)
        if not acquired:
            raise Exception("Code %s. Unable to acquire the repository lock when removing orphan files. You may try again!"%(lockId,))
        removed = []
        try:
            # Looked for again because the index could have changed while the lock was not held
            for paths in self.__find_orphans(olderThan):
                for path in paths:
                    try:
                        os.remove(path)
                        removed.append(os.path.relpath(path, self.__path))
                    except OSError:
                        # Another process may have removed it
                        pass
        finally:
            self.__locker.release_lock(lockId)
        return removed

    def create_repository(self, path, info=None, description=None, replace=False, allowNoneEmpty=True, raiseError=True):
        """
        create a repository in a directory. This method insures the creation of
        the directory in the system if it is missing.\n

        **N.B. If replace is True and an existing repository is found in path, create_repository erases ALL files and directories in path, including ones that are not tracked by the repository.**

        :Parameters:
            #. path (string): The real absolute path where to create the Repository.
               If '.' or an empty string is passed, the current working directory will be used.
            #. description (None, str): Repository main directory information.
            #. info (None, object): Repository information. It can
               be None or any pickle writable type of data.
            #. replace (boolean): Whether to replace an existing repository.
               The default False raises or returns failure instead. True
               erases everything in path first.
            #. allowNoneEmpty (boolean): Allow creating repository in none-empty
               directory.
            #. raiseError (boolean): Whether to raise encountered error instead
               of returning failure.

        :Returns:
            #. success (boolean): Whether creating repository was successful
            #. message (None, str): Any returned message.
        """
        if not (isinstance(raiseError, bool)):
            raise Exception("raiseError must be boolean")
        if not (isinstance(allowNoneEmpty, bool)):
            raise Exception("allowNoneEmpty must be boolean")
        if not (isinstance(replace, bool)):
            raise Exception("replace must be boolean")
        if not (isinstance(path, str)):
            raise Exception("path must be string")
        if info is None:
            info = ''
        try:
            pickle.dumps(info)
        except Exception as err:
            raise Exception("info must be None or any pickle writable type of data (%s)"%str(err))
        if description is None:
            description = ''
        if not (isinstance(description, str)):
            raise Exception("description must be None or a string")
        # get real path
        if path.strip() in ('','.'):
            path = os.getcwd()
        realPath = os.path.realpath( os.path.expanduser(path) )
        # reset if replace is set to True
        message = []
        if self.is_repository(realPath):
            if not replace:
                error = "A pyrep Repository already exists in the given path '%s'. Set replace to True to erase it and everything in that directory."%path
                if raiseError:
                    raise Exception(error)
                return False, error
            else:
                message.append("Existing pyrep repository existing in the given path '%s' has been replaced."%path)
                try:
                    for _df in os.listdir(realPath):
                        _p = os.path.join(realPath, _df)
                        if os.path.isdir(_p):
                            shutil.rmtree( _p )
                        else:
                            os.remove(_p)
                except Exception as err:
                    message.append("Unable to clean remove repository before create (%s)"%(str(err)))
                    return False, '\n'.join(message)
        if not os.path.isdir(realPath):
            os.makedirs(realPath, exist_ok=True)
        elif len(os.listdir(realPath)) and not allowNoneEmpty:
            return False, "Not allowed to create repository in a non empty directory"
        # reset repository
        oldRepo = self.__repo
        oldPath = self.__path
        self.reset()
        self.__path = realPath.rstrip(os.sep)
        self.__repo['repository_information'] = info
        # set locker
        error = None
        try:
            serverFile = os.path.join(self.__path, self.__repoLock)
            self.__start_locker(serverFile)
        except Exception as err:
            error = "Unable to start the repository locker (%s)"%(str(err),)
        # save repository
        if error is None:
            saved, saveError = self.save(description=description, raiseError=False)
            if not saved:
                error = "Unable to save repository (%s)"%(saveError,)
        if error is not None:
            if self.__locker is not None:
                try:
                    self.__locker.stop()
                except Exception:
                    # the locker may be only partially started
                    pass
            self.__repo   = oldRepo
            self.__path   = oldPath
            self.__locker = None
            message.append(error)
            message.append("Absolute path and directories might be created but no pyrep Repository is created. Previous repository state restored")
            if self.__path is not None:
                serverFile = os.path.join(self.__path, self.__repoLock)
                self.__start_locker(serverFile)
            if raiseError:
                raise Exception('\n'.join(message))
            return False, '\n'.join(message)
        # return
        return True, '\n'.join(message)

    def remove_repository(self, path=None, password=None, removeEmptyDirs=True):
        """
        Remove all repository from path along with all repository tracked files.

        :Parameters:
            #. path (None, string): The path the repository to remove.
            #. password (None, string): If path is not for this instance
               repository, a new Repository must be created and this
               password would be given upon instanciation
            #. removeEmptyDirs (boolean): Whether to remove remaining empty
               directories including repository one.
        """
        if not (isinstance(removeEmptyDirs, bool)):
            raise Exception("removeEmptyDirs must be boolean")
        if path is not None:
            if path != self.__path:
                repo = Repository(password=password)
                repo.load_repository(path)
            else:
                repo = self
        else:
            repo = self
        if not (repo.path is not None):
            raise Exception("path is not given and repository is not initialized")
        if not (repo.locker.isServer):
            raise Exception("It's not safe to remove repository tree from a client")
        if not (not len(repo.locker._clientsLUT)):
            raise Exception("It's not safe to remove repository tree when other instances are still connected")
        # remove repo files and directories
        for fdict in reversed(repo.get_repository_state()):
            relaPath   = list(fdict)[0]
            realPath   = os.path.join(repo.path, relaPath)
            path, name = os.path.split(realPath)
            if fdict[relaPath]['type'] == 'file':
                if os.path.isfile(realPath):
                    os.remove(realPath)
                if os.path.isfile(os.path.join(repo.path,path,self.__fileInfo%name)):
                    os.remove(os.path.join(repo.path,path,self.__fileInfo%name))
                if os.path.isfile(os.path.join(repo.path,path,self.__fileLock%name)):
                    os.remove(os.path.join(repo.path,path,self.__fileLock%name))
                if os.path.isfile(os.path.join(repo.path,path,self.__fileClass%name)):
                    os.remove(os.path.join(repo.path,path,self.__fileClass%name))
            elif fdict[relaPath]['type'] == 'dir':
                if os.path.isfile(os.path.join(realPath,self.__dirInfo)):
                    os.remove(os.path.join(realPath,self.__dirInfo))
                if os.path.isfile(os.path.join(realPath,self.__dirLock)):
                    os.remove(os.path.join(realPath,self.__dirLock))
                if not len(os.listdir(realPath)) and removeEmptyDirs:
                    shutil.rmtree( realPath )
        # remove repo information file
        if os.path.isfile(os.path.join(repo.path,self.__repoFile)):
            os.remove(os.path.join(repo.path,self.__repoFile))
        if os.path.isfile(os.path.join(repo.path,self.__repoLock)):
            os.remove(os.path.join(repo.path,self.__repoLock))
        # close repo first, the locker keeps its own lock file in the directory until it stops
        repo.close()
        if os.path.isfile(os.path.join(repo.path,self.__repoLock+'.lock')):
            os.remove(os.path.join(repo.path,self.__repoLock+'.lock'))
        if not len(os.listdir(repo.path)) and removeEmptyDirs:
            shutil.rmtree( repo.path )

    @path_required
    def save(self, description=None, raiseError=True, ntrials=3):
        """
        Save repository '.pyreprepo' to disk and create (if missing) or
        update (if description is not None) '.pyrepdirinfo'.

        :Parameters:
            #. description (None, str): Repository main directory information.
               If given will be replaced.
            #. raiseError (boolean): Whether to raise encountered error instead
               of returning failure.
            #. ntrials (int): The maximum number of attempts of the operation once its locks are held.
               Only an error that can pass by itself, such as a busy or interrupted call of the file
               system, is attempted again, after a pause that doubles with every attempt. Any other
               error fails at once, which also keeps your own dump and pull methods from running
               again after they failed. The message of a failure lists the error of every attempt.

        :Returns:
            #. success (bool): Whether saving was successful.
            #. error (None, string): Fail to save repository message in case
               saving is not successful. If success is True, error will be None.
        """
        if not (isinstance(raiseError, bool)):
            raise Exception("raiseError must be boolean")
        if not (isinstance(ntrials, int)):
            raise Exception("ntrials must be integer")
        if not (ntrials>0):
            raise Exception("ntrials must be >0")
        # get description
        if description is not None:
            if not (isinstance(description, str)):
                raise Exception("description must be None or a string")
        dirInfoPath = os.path.join(self.__path, self.__dirInfo)
        if description is None and not os.path.isfile(dirInfoPath):
            description = ''
        # create and acquire lock
        acquired, lockId = self.__acquire_lock(self.__path)
        # check if acquired.
        if not acquired:
            m = "code %s. Unable to acquire the lock when calling 'save'. You may try again!"%(lockId,)
            if raiseError:
                raise Exception(m)
            return False, m
        # save repository
        attempts = []
        for _trial in range(ntrials):
            try:
                # open file
                repoInfoPath = os.path.join(self.__path, self.__repoFile)
                error = None
                self.__save_dirinfo(description=description, dirInfoPath=dirInfoPath)
                # load and update repository info if existing
                if os.path.isfile(repoInfoPath):
                    repo = self.__load_repository_pickle_file(repoInfoPath)
                    self.__repo['walk_repo'] = repo['walk_repo']
                # create repository
                self.__repo["last_update_utctime"] = time.time()
                write_pickle_atomically(repoInfoPath, self.__repo, self._DEFAULT_PICKLE_PROTOCOL)
            except Exception as err:
                error = "Unable to save repository (%s)"%err
                if self.DEBUG_PRINT_FAILED_TRIALS: print("Trial %i failed in Repository.%s (%s). Set Repository.DEBUG_PRINT_FAILED_TRIALS to False to mute"%(_trial, inspect.stack()[1][3], str(error)))
                attempts.append(error)
                error = describe_attempts(attempts)
                if not should_retry(err, _trial, ntrials):
                    break
            else:
                break
        # release lock
        self.__locker.release_lock(lockId)
        # return
        if error is not None and raiseError:
            raise Exception(error)
        return error is None, error


    def is_name_allowed(self, path):
        """
        Get whether creating a file or a directory from the basenane of the given
        path is allowed

        :Parameters:
            #. path (str): The absolute or relative path or simply the file
               or directory name.

        :Returns:
            #. allowed (bool): Whether name is allowed.
            #. message (None, str): Reason for the name to be forbidden.
        """
        if not (isinstance(path, str)):
            raise Exception("given path must be a string")
        name = os.path.basename(path)
        if not len(name):
            return False, "empty name is not allowed"
        if '\0' in name:
            return False, "a name cannot contain a null character"
        # exact match
        for em in [self.__repoLock,self.__repoFile,self.__dirInfo,self.__dirLock,self.__repoJournal]:
            if name == em:
                return False, "name '%s' is reserved for pyrep internal usage"%em
        if name.startswith('.pyreptmp_'):
            return False, "names starting with '.pyreptmp_' are reserved for pyrep internal usage"
        # pattern match
        for pm in [self.__fileInfo,self.__fileClass,self.__fileLock,self.__fileJournal]:
            if name == pm or (name.endswith(pm[3:]) and name.startswith('.')):
                return False, "name pattern '%s' is not allowed as result may be reserved for pyrep internal usage"%pm
        # name is ok
        return True, None

    def __root_refusal(self, raiseError, *relativePaths):
        """
        Refuses a relative path that is the repository directory itself where a file is needed. It must be
        asked before any lock is taken, because the repository directory is also the path of the repository lock.

        :Parameters:
            #. raiseError (boolean): Whether to raise the refusal instead of returning it.
            #. relativePaths (str): The normalised relative paths to check.

        :Returns:
            #. refusal (None, tuple): None when none of the paths is the repository directory, otherwise
               the failure tuple of False and the message.
        """
        if '' not in relativePaths:
            return None
        error = "The repository directory is not a file"
        if raiseError:
            raise Exception(error)
        return False, error

    def to_repo_relative_path(self, path, split=False):
        """
        Given a path, return relative path to directory

        :Parameters:
            #. path (str): Path as a string
            #. split (boolean): Whether to split path to its components

        :Returns:
            #. relativePath (str, list): Relative path as a string or as a list
               of components if split is True
        """
        # Checked first because on some python versions normpath silently cuts a path at a null character
        if '\0' in path:
            raise Exception("Path '%s' contains a null character"%path.replace('\0', '\\0'))
        path = os.path.normpath(path)
        if path == '.':
            path = ''
        path = path.split(self.__path)[-1].strip(os.sep)
        # normpath keeps leading '..' components, which would point outside the repository
        if '..' in path.split(os.sep):
            raise Exception("Path '%s' points outside of the repository"%path)
        # a symlink inside the repository can still lead outside of it
        realTarget = os.path.realpath(os.path.join(self.__path, path))
        if realTarget != self.__path and not realTarget.startswith(self.__path + os.sep):
            raise Exception("Path '%s' resolves outside of the repository through a symbolic link"%path)
        if split:
            return path.split(os.sep)
        else:
            return path

    @path_required
    def get_repository_state(self, relaPath=None):
        """
        Get a list representation of repository state along with useful
        information. List state is ordered relativeley to directories level

        :Parameters:
            #. relaPath (None, str): relative directory path from where to
               start. If None all repository representation is returned.

        :Returns:
            #. state (list): List representation of the repository.
               List items are all dictionaries. Every dictionary has a single
               key which is the file or the directory name and the value is a
               dictionary of information including:

                   * 'type': the type of the tracked item, either 'file' or 'dir'
                   * 'exists': whether file or directory actually exists on disk
                   * 'pyrepfileinfo': In case of a file whether .%s_pyrepfileinfo exists
                   * 'pyrepdirinfo': In case of a directory whether .pyrepdirinfo exists
        """
        state = self.__get_repository_state(relaPath)
        # An empty state means that the directory is not tracked here, which may be because the list is old
        if len(state) == 0 and self.__refresh_if_stale():
            state = self.__get_repository_state(relaPath)
        return state

    def __get_repository_state(self, relaPath):
        """
        Builds the state from the list this instance holds, without looking for changes made by others. Methods
        that hold locks use it, because refreshing would take the repository lock again.
        """
        state = []
        def _walk_dir(relaPath, dirList):
            dirDict = {'type':'dir',
                       'exists':os.path.isdir(os.path.join(self.__path,relaPath)),
                       'pyrepdirinfo':os.path.isfile(os.path.join(self.__path,relaPath,self.__dirInfo)),
                      }
            state.append({relaPath:dirDict})
            # loop files and dirobjects
            for fname in sorted([f for f in dirList if isinstance(f, str)]):
                relaFilePath = os.path.join(relaPath,fname)
                realFilePath = os.path.join(self.__path,relaFilePath)
                fileDict = {'type':'file',
                            'exists':os.path.isfile(realFilePath),
                            'pyrepfileinfo':os.path.isfile(os.path.join(self.__path,relaPath,self.__fileInfo%fname)),
                           }
                state.append({relaFilePath:fileDict})
            # loop directories
            for ddict in sorted([d for d in dirList if isinstance(d, dict)], key=lambda k: list(k)[0]):
                dirname = list(ddict)[0]
                _walk_dir(relaPath=os.path.join(relaPath,dirname), dirList=ddict[dirname])
        # call recursive _walk_dir
        if relaPath is not None:
            if not (isinstance(relaPath, str)):
                raise Exception("relaPath must be None or a str")
            relaPath = self.to_repo_relative_path(path=relaPath, split=False)
        # The empty relative path is the repository itself, which remove_directory asks for when the parent is the root
        if relaPath is None or relaPath == '':
            _walk_dir(relaPath='', dirList=self.__repo['walk_repo'])
        else:
            spath    = relaPath.split(os.sep)
            dirList  = self.__repo['walk_repo']
            while len(spath):
                dirname = spath.pop(0)
                dList   = [d for d in dirList if isinstance(d, dict)]
                if not len(dList):
                    dirList = None
                    break
                cDict = [d for d in dList if dirname in d]
                if not len(cDict):
                    dirList = None
                    break
                dirList = cDict[0][dirname]
            if dirList is not None:
                _walk_dir(relaPath=relaPath, dirList=dirList)
        # return state list
        return state

    def get_repository_directory(self, relativePath):
        """
        Get repository directory list copy.

        :Parameters:
            #. relativePath (string): The relative to the repository path .

        :Returns:
            #. dirList (None, list): List of directories and files in repository
               directory. If directory is not tracked in repository None is
               returned
        """
        return copy.deepcopy(self.__get_directory_or_refresh(relativePath))

    def get_file_info(self, relativePath):
        """
        Get file information dict from the repository given its relative path.

        :Parameters:
            #. relativePath (string): The relative to the repository path of
               the file.

        :Returns:
            #. info (None, dictionary): The file information dictionary.
               If None, it means an error has occurred.
            #. errorMessage (string): The error message if any error occurred.
        """
        relativePath = self.to_repo_relative_path(path=relativePath, split=False)
        fileName     = os.path.basename(relativePath)
        isRepoFile, _, infoOnDisk, _ = self.is_repository_file(relativePath)
        if not isRepoFile:
            return None, "file is not a registered repository file."
        if not infoOnDisk:
            return None, "file is a registered repository file but info file missing"
        fileInfoPath = os.path.join(self.__path,os.path.dirname(relativePath),self.__fileInfo%fileName)
        try:
            with open(fileInfoPath, 'rb') as fd:
                info = pickle.load(fd)
        except Exception as err:
            return None, "Unable to read file info from disk (%s)"%str(err)
        return info, ''


    def is_repository_directory(self, relativePath):
        """
        Get whether directory is registered in repository.

        :Parameters:
            #. relativePath (string): The relative to the repository path.

        :Returns:
            #. result (boolean): Whether directory is tracked and registered.
        """
        return self.__get_directory_or_refresh(relativePath) is not None

    def __is_repository_directory(self, relativePath):
        """
        Tells whether a directory is tracked in the list this instance holds, without looking at the disk. Methods
        that hold locks use it, because refreshing would take the repository lock again.
        """
        return self.__get_repository_directory(relativePath) is not None


    def is_repository_file(self, relativePath):
        """
        Check whether a given relative path is a repository file path

        :Parameters:
            #. relativePath (string): File relative path

        :Returns:
            #. isRepoFile (boolean): Whether file is a repository file.
            #. isFileOnDisk (boolean): Whether file is found on disk.
            #. isFileInfoOnDisk (boolean): Whether file info is found on disk.
            #. isFileClassOnDisk (boolean): Whether file class is found on disk.
        """
        result = self.__is_repository_file(relativePath)
        # Tracked but missing on disk is also what a file removed by another instance looks like from an old list
        isComplete = result[0] is True and result[1] is True and result[2] is True
        if isComplete is False and self.__refresh_if_stale():
            result = self.__is_repository_file(relativePath)
        return result

    def __is_repository_file(self, relativePath):
        """
        Checks a file against the list this instance holds, without looking for changes made by others. Methods
        that hold locks use it, because refreshing would take the repository lock again.
        """
        relativePath  = self.to_repo_relative_path(path=relativePath, split=False)
        if relativePath == '':
            return False, False, False, False
        relaDir, name = os.path.split(relativePath)
        fileOnDisk    = os.path.isfile(os.path.join(self.__path, relativePath))
        infoOnDisk    = os.path.isfile(os.path.join(self.__path,os.path.dirname(relativePath),self.__fileInfo%name))
        classOnDisk   = os.path.isfile(os.path.join(self.__path,os.path.dirname(relativePath),self.__fileClass%name))
        cDir          = self.__repo['walk_repo']
        if len(relaDir):
            for dirname in relaDir.split(os.sep):
                dList = [d for d in cDir if isinstance(d, dict)]
                if not len(dList):
                    cDir = None
                    break
                cDict = [d for d in dList if dirname in d]
                if not len(cDict):
                    cDir = None
                    break
                cDir = cDict[0][dirname]
        if cDir is None:
            return False, fileOnDisk, infoOnDisk, classOnDisk
        if str(name) not in [str(i) for i in cDir]:
            return False, fileOnDisk, infoOnDisk, classOnDisk
        # this is a repository registered file. check whether all is on disk
        return True, fileOnDisk, infoOnDisk, classOnDisk

    @path_required
    def walk_files_path(self, relativePath="", fullPath=False, recursive=False):
        """
        Walk the repository relative path and yield file relative/full path.

        :Parameters:
            #. relativePath (string): The relative path from which start the walk.
            #. fullPath (boolean): Whether to return full or relative path.
            #. recursive (boolean): Whether walk all directories files recursively
        """
        if not (isinstance(fullPath, bool)):
            raise Exception("fullPath must be boolean")
        if not (isinstance(recursive, bool)):
            raise Exception("recursive must be boolean")
        relativePath = self.to_repo_relative_path(path=relativePath, split=False)
        dirList      = self.__get_directory_or_refresh(relativePath)
        if not (dirList is not None):
            raise Exception("given relative path '%s' is not a repository directory"%relativePath)
        # walk recursive function
        def _walk(rpath, dlist,recursive):
            # walk files
            for fname in dlist:
                if isinstance(fname, str):
                    if fullPath:
                        yield os.path.join(self.__path, rpath, fname)
                    else:
                        yield os.path.join(rpath, fname)
            if recursive:
                for ddict in dlist:
                    if isinstance(ddict, dict):
                        dname = list(ddict)[0]
                        for p in _walk(rpath=os.path.join(rpath,dname), dlist=ddict[dname],recursive=recursive):
                            yield p
        # walk all files
        return _walk(rpath=relativePath, dlist=dirList, recursive=recursive)

    def walk_files_info(self, relativePath="", fullPath=False, recursive=False):
        """
        Walk the repository relative path and yield tuple of two items where
        first item is file relative/full path and second item is file info.
        If file info is not found on disk, second item will be None.

        :Parameters:
            #. relativePath (string): The relative path from which start the walk.
            #. fullPath (boolean): Whether to return full or relative path.
            #. recursive (boolean): Whether walk all directories files recursively
        """
        if not (isinstance(fullPath, bool)):
            raise Exception("fullPath must be boolean")
        if not (isinstance(recursive, bool)):
            raise Exception("recursive must be boolean")
        relativePath = self.to_repo_relative_path(path=relativePath, split=False)
        for relaPath in self.walk_files_path(relativePath=relativePath, fullPath=False, recursive=recursive):
            fpath, fname = os.path.split(relaPath)
            fileInfoPath = os.path.join(self.__path,fpath,self.__fileInfo%fname)
            if os.path.isfile(fileInfoPath):
                with open(fileInfoPath, 'rb') as fd:
                    info = pickle.load(fd)
            else:
                info = None
            if fullPath:
                yield (os.path.join(self.__path, relaPath), info)
            else:
                yield (relaPath, info)


    def walk_directories_path(self, relativePath="", fullPath=False, recursive=False):
        """
        Walk repository relative path and yield directory relative/full path

        :Parameters:
            #. relativePath (string): The relative path from which start the walk.
            #. fullPath (boolean): Whether to return full or relative path.
            #. recursive (boolean): Whether walk all directories files recursively.
        """
        if not (isinstance(fullPath, bool)):
            raise Exception("fullPath must be boolean")
        if not (isinstance(recursive, bool)):
            raise Exception("recursive must be boolean")
        relativePath = self.to_repo_relative_path(path=relativePath, split=False)
        dirList      = self.__get_directory_or_refresh(relativePath)
        if not (dirList is not None):
            raise Exception("given relative path '%s' is not a repository directory"%relativePath)
        # walk recursive function
        def _walk(rpath, dlist,recursive):
            # walk files
            for ddict in dlist:
                if isinstance(ddict, dict):
                    dname = list(ddict)[0]
                    if fullPath:
                        yield os.path.join(self.__path, rpath, dname)
                    else:
                        yield os.path.join(rpath, dname)
            if recursive:
                for ddict in dlist:
                    if isinstance(ddict, dict):
                        dname = list(ddict)[0]
                        for p in _walk(rpath=os.path.join(rpath,dname), dlist=ddict[dname],recursive=recursive):
                            yield p
        # walk all files
        return _walk(rpath=relativePath, dlist=dirList, recursive=recursive)

    def walk_directories_info(self, relativePath="", fullPath=False, recursive=False):
        """
        Walk the repository relative path and yield tuple of two items where
        first item is directory relative/full path and second item is directory
        info. If directory file info is not found on disk, second item will be None.

        :Parameters:
            #. relativePath (string): The relative path from which start the walk.
            #. fullPath (boolean): Whether to return full or relative path.
            #. recursive (boolean): Whether walk all directories files recursively.
        """
        if not (isinstance(fullPath, bool)):
            raise Exception("fullPath must be boolean")
        if not (isinstance(recursive, bool)):
            raise Exception("recursive must be boolean")
        relativePath = self.to_repo_relative_path(path=relativePath, split=False)
        # walk directories
        for dpath in self.walk_directories_path(relativePath=relativePath, fullPath=False, recursive=recursive):
            dirInfoPath = os.path.join(self.__path,dpath,self.__dirInfo)
            if os.path.isfile(dirInfoPath):
                with open(dirInfoPath, 'rb') as fd:
                    info = pickle.load(fd)
            else:
                info = None
            if fullPath:
                yield (os.path.join(self.__path, dpath), info)
            else:
                yield (dpath, info)

    @path_required
    def create_package(self, path=None, name=None, mode=None):
        """
        Create a tar file package of all the repository files and directories.
        Only files and directories that are tracked in the repository
        are stored in the package tar file.

        **N.B. On some systems packaging requires root permissions.**

        :Parameters:
            #. path (None, string): The real absolute path where to create the
               package. If None, it will be created in the same directory as
               the repository. If '.' or an empty string is passed, the current
               working directory will be used.
            #. name (None, string): The name to give to the package file
               If None, the package directory name will be used with the
               appropriate extension added.
            #. mode (None, string): The writing mode of the tarfile.
               If None, automatically the best compression mode will be chose.
               Available modes are ('w', 'w:', 'w:gz', 'w:bz2')
        """
        # check mode
        if not (mode in (None, 'w', 'w:', 'w:gz', 'w:bz2')):
            raise Exception('unkown archive mode %s'%str(mode))
        if mode is None:
            mode = 'w:'
        # get root
        if path is None:
            root = os.path.split(self.__path)[0]
        elif path.strip() in ('','.'):
            root = os.getcwd()
        else:
            root = os.path.realpath( os.path.expanduser(path) )
        if not (os.path.isdir(root)):
            raise Exception('absolute path %s is not a valid directory'%path)
        # get name
        if name is None:
            ext = mode.split(":")
            if len(ext) == 2:
                if len(ext[1]):
                    ext = ".tar."+ext[1]
                else:
                    ext = '.tar'
            else:
                ext = '.tar'
            name = os.path.split(self.__path)[1]+ext
        # create tar file
        tarfilePath = os.path.join(root, name)
        try:
            tarHandler = tarfile.TarFile.open(tarfilePath, mode=mode)
        except Exception as e:
            raise Exception("Unable to create package (%s)"%e)
        try:
            # the repository root directory info
            tarHandler.add(os.path.join(self.__path,self.__dirInfo), arcname=self.__dirInfo)
            # walk directory and create empty directories
            for dpath in sorted(list(self.walk_directories_path(recursive=True))):
                t = tarfile.TarInfo( dpath )
                t.type = tarfile.DIRTYPE
                # directories need the execute bit or they cannot be opened after unpacking
                t.mode = 0o755
                tarHandler.addfile(t)
                tarHandler.add(os.path.join(self.__path,dpath,self.__dirInfo), arcname=os.path.join(dpath,self.__dirInfo))
            # walk files and add to tar
            for fpath in self.walk_files_path(recursive=True):
                relaPath, fname = os.path.split(fpath)
                tarHandler.add(os.path.join(self.__path,fpath), arcname=fpath)
                tarHandler.add(os.path.join(self.__path,relaPath,self.__fileInfo%fname), arcname=os.path.join(relaPath,self.__fileInfo%fname))
                tarHandler.add(os.path.join(self.__path,relaPath,self.__fileClass%fname), arcname=os.path.join(relaPath,self.__fileClass%fname))
            # save the main repository file under its real name so the package opens as a repository
            tarHandler.add(os.path.join(self.__path,self.__repoFile), arcname=self.__repoFile)
        finally:
            tarHandler.close()


    @path_required
    def add_directory(self, relativePath, description=None, clean=False,
                            raiseError=True, ntrials=3):
        """
        Add a directory in the repository and creates its attribute in the
        Repository with utc timestamp. It insures adding all the missing
        directories in the path.

        :Parameters:
            #. relativePath (string): The relative to the repository path to
               where directory must be added.
            #. description (None, string): Any random description about the
               added directory.
            #. clean (boolean): Whether to remove existing non repository
               tracked files and folders in all created directory chain tree.
            #. raiseError (boolean): Whether to raise encountered error instead
               of returning failure.
            #. ntrials (int): The maximum number of attempts of the operation once its locks are held.
               Only an error that can pass by itself, such as a busy or interrupted call of the file
               system, is attempted again, after a pause that doubles with every attempt. Any other
               error fails at once, which also keeps your own dump and pull methods from running
               again after they failed. The message of a failure lists the error of every attempt.

        :Returns:
            #. success (boolean): Whether adding the directory was successful.
            #. message (None, string): Reason why directory was not added or
               random information.
        """
        if not (isinstance(raiseError, bool)):
            raise Exception("raiseError must be boolean")
        if not (isinstance(relativePath, str)):
            raise Exception("relativePath must be a string")
        if description is not None:
            if not (isinstance(description, str)):
                raise Exception("description must be None or a string")
        if not (isinstance(ntrials, int)):
            raise Exception("ntrials must be integer")
        if not (ntrials>0):
            raise Exception("ntrials must be >0")
        # normalise path
        path = self.to_repo_relative_path(path=relativePath, split=False)
        # whether to replace
        if self.__is_repository_directory(path):
            return True, "Directory is already tracked in repository"
        # check whether name is allowed
        allowed, reason = self.is_name_allowed(path)
        if not allowed:
            if raiseError:
                raise Exception(reason)
            return False, reason
        # lock repository
        acquired, repoLockId = self.__acquire_lock(self.__path)
        if not acquired:
            m = "code %s. Unable to acquire the lock to add directory. You may try again!"%(repoLockId,)
            if raiseError:
                raise Exception(m)
            return False,m
        # load repository info
        attempts = []
        for _trial in range(ntrials):
            try:
                repo = self.__load_repository_pickle_file(os.path.join(self.__path, self.__repoFile))
                self.__repo['walk_repo'] = repo['walk_repo']
            except Exception as err:
                error = str(err)
                if self.DEBUG_PRINT_FAILED_TRIALS: print("Trial %i failed in Repository.%s (%s). Set Repository.DEBUG_PRINT_FAILED_TRIALS to False to mute"%(_trial, inspect.stack()[1][3], str(error)))
                attempts.append(error)
                error = describe_attempts(attempts)
                if not should_retry(err, _trial, ntrials):
                    break
            else:
                error = None
                break
        if error is not None:
            self.__locker.release_lock(repoLockId)
            if raiseError:
                raise Exception(error)
            return False, error
        # create directories
        error     = None
        posList   = self.__repo['walk_repo']
        dirPath   = self.__path
        spath     = path.split(os.sep)
        for idx, name in enumerate(spath):
            dirLockId = None
            # create and acquire directory lock
            if dirPath != self.__path:
                acquired, dirLockId = self.__acquire_lock(dirPath)
                if not acquired:
                    error = "Code %s. Unable to acquire the lock when adding '%s'. All prior relative directories were added. You may try again, to finish adding directory"%(dirLockId,dirPath)
                    break
            # add to directory
            attempts = []
            for _trial in range(ntrials):
                try:
                    dirPath = os.path.join(dirPath, name)
                    riPath  = os.path.join(dirPath, self.__dirInfo)
                    dList   = [d for d in posList if isinstance(d, dict)]
                    dList   = [d for d in dList if name in d]
                    # clean directory
                    if not len(dList) and clean and os.path.exists(dirPath):
                        try:
                            shutil.rmtree( dirPath, ignore_errors=True )
                        except Exception as err:
                            error = "Unable to clean directory '%s' (%s)"%(dirPath, err)
                            break
                    # create directory
                    if not os.path.exists(dirPath):
                        try:
                            os.mkdir(dirPath)
                        except Exception as err:
                            error = "Unable to create directory '%s' (%s)"%(dirPath, err)
                            break
                    # create and dump dirinfo
                    self.__save_dirinfo(description=[None, description][idx==len(spath)-1],
                                        dirInfoPath=riPath, create=True)
                    # update directory list
                    if not len(dList):
                        rsd = {name:[]}
                        posList.append(rsd)
                        posList = rsd[name]
                    else:
                        if not (len(dList) == 1):
                            raise Exception("Same directory name dict is found twice. This should'n have happened. Report issue")
                        posList = dList[0][name]
                except Exception as err:
                    error = "Unable to create directory '%s' info file (%s)"%(dirPath, str(err))
                    if self.DEBUG_PRINT_FAILED_TRIALS: print("Trial %i failed in Repository.%s (%s). Set Repository.DEBUG_PRINT_FAILED_TRIALS to False to mute"%(_trial, inspect.stack()[1][3], str(error)))
                    attempts.append(error)
                    error = describe_attempts(attempts)
                    if not should_retry(err, _trial, ntrials):
                        break
                else:
                    break
            if dirLockId is not None:
                self.__locker.release_lock(dirLockId)
            # break from main path loop
            if error is not None:
                break
        # save __repo
        if error is None:
            try:
                _, error = self.__save_repository_pickle_file(lockFirst=False, raiseError=False)
            except Exception as err:
                error = str(err)
                pass
        # release locks
        if dirLockId is not None:
            self.__locker.release_lock(dirLockId)
        self.__locker.release_lock(repoLockId)
        # check and return
        if error is not None and raiseError:
            raise Exception(error)
        return error is None, error

    def get_repository_parent_directory(self, relativePath):
        """
        Get repository parent directory list copy.

        :Parameters:
            #. relativePath (string): The relative to the repository path .

        :Returns:
            #. dirList (None, list): List of directories and files in repository
               parent directory. If directory is not tracked in repository
               None is returned
        """
        return copy.deepcopy(self.__get_directory_or_refresh(relativePath, parent=True))

    @path_required
    def remove_directory(self, relativePath, clean=False, raiseError=True, ntrials=3):
        """
        Remove directory from repository tracking.

        :Parameters:
            #. relativePath (string): The relative to the repository path of the
               directory to remove from the repository.
            #. clean (boolean): Whether to os remove directory. If False only
               tracked files will be removed along with left empty directories.
            #. raiseError (boolean): Whether to raise encountered error instead
               of returning failure.
            #. ntrials (int): The maximum number of attempts of the operation once its locks are held.
               Only an error that can pass by itself, such as a busy or interrupted call of the file
               system, is attempted again, after a pause that doubles with every attempt. Any other
               error fails at once, which also keeps your own dump and pull methods from running
               again after they failed. The message of a failure lists the error of every attempt.

        :Returns:
            #. success (boolean): Whether removing the directory was successful.
            #. reason (None, string): Reason why directory was not removed.
        """
        if not (isinstance(raiseError, bool)):
            raise Exception("raiseError must be boolean")
        if not (isinstance(clean, bool)):
            raise Exception("clean must be boolean")
        if not (isinstance(ntrials, int)):
            raise Exception("ntrials must be integer")
        if not (ntrials>0):
            raise Exception("ntrials must be >0")
        # normalise path
        relativePath = self.to_repo_relative_path(path=relativePath, split=False)
        parentPath, dirName = os.path.split(relativePath)
        # check if this is main repository directory
        if relativePath == '':
            return False, "Removing main repository directory is not allowed"
        # check if this is a repository directory
        if not self.__is_repository_directory(relativePath):
            return False, "Given relative path '%s' is not a repository path"%relativePath
        # check if directory actually exists on disk
        realPath = os.path.join(self.__path,relativePath)
        if not os.path.isdir(realPath):
            error = "Repository relative directory '%s' seems to be missing. call maintain_repository to fix all issues"%(realPath,)
            if raiseError:
                raise Exception(error)
            return False, error
        # The repository root is already covered by the repository lock taken below
        dirLockId = None
        if parentPath != '':
            acquired, dirLockId = self.__acquire_lock(os.path.join(self.__path,parentPath))
            if not acquired:
                error = "Code %s. Unable to acquire the parent directory lock when removing '%s'. You may try again!"%(dirLockId, relativePath)
                if raiseError:
                    raise Exception(error)
                return False, error
        # lock repository
        acquired, repoLockId = self.__acquire_lock(self.__path)
        if not acquired:
            if dirLockId is not None:
                self.__locker.release_lock(dirLockId)
            error = "Code %s. Unable to acquire the repository lock when removing '%s'. You may try again!"%(repoLockId, relativePath)
            if raiseError:
                raise Exception(error)
            return False, error
        # remove directory
        attempts = []
        for _trial in range(ntrials):
            error = None
            try:
                # Reload because another process may have changed the tracked files since the last read
                repo = self.__load_repository_pickle_file(os.path.join(self.__path, self.__repoFile))
                self.__repo['walk_repo'] = repo['walk_repo']
                dirList = self.__get_repository_parent_directory(relativePath=relativePath)
                if not (dirList is not None):
                    raise Exception("Given relative path '%s' is not a repository directory"%(relativePath,))
                stateBefore = self.__get_repository_state(relaPath=parentPath)
                _files = [f for f in dirList if isinstance(f, str)]
                _dirs  = [d for d in dirList if isinstance(d, dict)]
                _dirs  = [d for d in dirList if isinstance(d, dict) and dirName not in d]
                _ = [dirList.pop(0) for _ in range(len(dirList))]
                dirList.extend(_files)
                dirList.extend(_dirs)
                # Nothing is deleted before the index is saved, so a crash never leaves a tracked directory without its files
                stateAfter = None if clean else self.__get_repository_state(relaPath=parentPath)
            except Exception as err:
                error = str(err)
                if self.DEBUG_PRINT_FAILED_TRIALS: print("Trial %s failed in Repository.%s (%s). Set Repository.DEBUG_PRINT_FAILED_TRIALS to False to mute"%(_trial, inspect.stack()[1][3], str(error)))
                attempts.append(error)
                error = describe_attempts(attempts)
                if not should_retry(err, _trial, ntrials):
                    break
            else:
                break
        # return
        leftovers = None
        if error is None:
            _, error = self.__save_repository_pickle_file(lockFirst=False, raiseError=False)
            if error is None:
                # The index no longer lists the directory, now its files can go
                try:
                    if clean:
                        shutil.rmtree(realPath)
                    else:
                        success, errors = self.__clean_before_after(stateBefore=stateBefore, stateAfter=stateAfter, keepNoneEmptyDirectory=True)
                        if not success:
                            leftovers = "\n".join(errors)
                except Exception as err:
                    leftovers = str(err)
                if leftovers is not None:
                    leftovers = "The directory is removed from the repository but could not be deleted from disk (%s)"%(leftovers,)
            else:
                self.__resync_index()
        # release locks
        if dirLockId is not None:
            self.__locker.release_lock(dirLockId)
        self.__locker.release_lock(repoLockId)
        # check and return
        if error is not None and raiseError:
            raise Exception("Unable to remove directory '%s' after %i trials (%s)"%(relativePath, ntrials, error,))
        return error is None, error if error is not None else leftovers


    @path_required
    def rename_directory(self, relativePath, newName, raiseError=True, ntrials=3):
        """
        Rename a directory in the repository. It insures renaming the directory in the system.

        :Parameters:
            #. relativePath (string): The relative to the repository path of
               the directory to be renamed.
            #. newName (string): The new directory name.
            #. raiseError (boolean): Whether to raise encountered error instead
               of returning failure.
            #. ntrials (int): The maximum number of attempts of the operation once its locks are held.
               Only an error that can pass by itself, such as a busy or interrupted call of the file
               system, is attempted again, after a pause that doubles with every attempt. Any other
               error fails at once, which also keeps your own dump and pull methods from running
               again after they failed. The message of a failure lists the error of every attempt.

        :Returns:
            #. success (boolean): Whether renaming the directory was successful.
            #. message (None, string): Some explanatory message or error reason
               why directory was not renamed.
        """
        if not (isinstance(raiseError, bool)):
            raise Exception("raiseError must be boolean")
        if not (isinstance(ntrials, int)):
            raise Exception("ntrials must be integer")
        if not (ntrials>0):
            raise Exception("ntrials must be >0")
        relativePath = self.to_repo_relative_path(path=relativePath, split=False)
        parentPath, dirName = os.path.split(relativePath)
        if relativePath == '':
            error = "Renaming main repository directory is not allowed"
            if raiseError:
                raise Exception(error)
            return False, error
        # The new name replaces the last path component, so it must be one name and not a path
        isSingleName = os.path.basename(newName) == newName and newName not in ('', '.', '..')
        allowed, reason = self.is_name_allowed(newName) if isSingleName else (False, "new name '%s' must be a single name without separators"%(newName,))
        if not allowed:
            if raiseError:
                raise Exception(reason)
            return False, reason
        realPath = os.path.join(self.__path,relativePath)
        newRealPath = os.path.join(os.path.dirname(realPath), newName)
        if os.path.isdir(newRealPath):
            error = "New directory path '%s' already exist"%(newRealPath,)
            if raiseError:
                raise Exception(error)
            return False, error
        # The repository root is already covered by the repository lock taken below
        dirLockId = None
        if parentPath != '':
            acquired, dirLockId = self.__acquire_lock(os.path.join(self.__path,parentPath))
            if not acquired:
                error = "Code %s. Unable to acquire the parent directory lock when renaming '%s'. You may try again!"%(dirLockId, relativePath)
                if raiseError:
                    raise Exception(error)
                return False, error
        error = None
        # lock repository
        acquired, repoLockId = self.__acquire_lock(self.__path)
        if not acquired:
            if dirLockId is not None:
                self.__locker.release_lock(dirLockId)
            error = "Code %s. Unable to acquire the repository lock when renaming '%s'. You may try again!"%(repoLockId, relativePath)
            if raiseError:
                raise Exception(error)
            return False, error
        # load repository info
        attempts = []
        for _trial in range(ntrials):
            try:
                repo = self.__load_repository_pickle_file(os.path.join(self.__path, self.__repoFile))
                self.__repo['walk_repo'] = repo['walk_repo']
            except Exception as err:
                error = str(err)
                if self.DEBUG_PRINT_FAILED_TRIALS: print("Trial %i failed in Repository.%s (%s). Set Repository.DEBUG_PRINT_FAILED_TRIALS to False to mute"%(_trial, inspect.stack()[1][3], str(error)))
                attempts.append(error)
                error = describe_attempts(attempts)
                if not should_retry(err, _trial, ntrials):
                    break
            else:
                error = None
                break
        if error is not None:
            if dirLockId is not None:
                self.__locker.release_lock(dirLockId)
            self.__locker.release_lock(repoLockId)
            if raiseError:
                raise Exception(error)
            return False, error
        # rename directory
        journalPath = os.path.join(self.__path, self.__repoJournal)
        attempts    = []
        for _trial in range(ntrials):
            error = None
            try:
                dirList = self.__get_repository_parent_directory(relativePath=relativePath)
                if not (dirList is not None):
                    raise Exception("Given relative path '%s' is not a repository directory"%(relativePath,))
                # change dirName in dirList
                _dirDict = [nd for nd in dirList  if isinstance(nd,dict)]
                _dirDict = [nd for nd in _dirDict if dirName in nd]
                if len(_dirDict) == 0:
                    raise Exception("Given relative path '%s' is not a repository directory"%(relativePath,))
                if not (len(_dirDict) == 1):
                    raise Exception("Directory '%s' is found more than once in the repository. Please report issue"%(relativePath,))
                # The journal makes the rename and the saving of the index one operation, whatever happens in between
                write_journal(journalPath, 'rename_directory', {'parent': parentPath, 'old': dirName, 'new': newName}, self._DEFAULT_PICKLE_PROTOCOL)
                os.rename(realPath, newRealPath)
                # update dirList
                _dirDict[0][newName] = _dirDict[0][dirName]
                _dirDict[0].pop(dirName)
                # update and dump dirinfo
                self.__save_dirinfo(description=None, dirInfoPath=parentPath, create=False)
            except Exception as err:
                error = str(err)
                if self.DEBUG_PRINT_FAILED_TRIALS: print("Trial %i failed in Repository.%s (%s). Set Repository.DEBUG_PRINT_FAILED_TRIALS to False to mute"%(_trial, inspect.stack()[1][3], str(error)))
                attempts.append(error)
                error = describe_attempts(attempts)
                if not should_retry(err, _trial, ntrials):
                    break
            else:
                error = None
                break
        if error is None:
            _, error = self.__save_repository_pickle_file(lockFirst=False, raiseError=False)
        # Settle the journal: the rename is done, or it never happened, or it is put back
        if os.path.isfile(journalPath):
            oldExists, newExists = os.path.isdir(realPath), os.path.isdir(newRealPath)
            if error is not None and newExists and not oldExists:
                try:
                    os.rename(newRealPath, realPath)
                    oldExists, newExists = True, False
                except OSError:
                    # The journal stays, and the next lock completes the rename
                    pass
            if error is None or (oldExists and not newExists):
                self.__remove_files([journalPath])
        if error is not None:
            self.__resync_index()
        # release locks
        if dirLockId is not None:
            self.__locker.release_lock(dirLockId)
        self.__locker.release_lock(repoLockId)
        # check and return
        if error is not None and raiseError:
            raise Exception("Unable to rename directory '%s' to '%s' after %i trials (%s)"%(relativePath, newName, ntrials, error,))
        return error is None, error

    @path_required
    def copy_directory(self, relativePath, newRelativePath,
                             overwrite=False, raiseError=True, ntrials=3):
        """
        Copy a directory in the repository. New directory must not exist.

        :Parameters:
            #. relativePath (string): The relative to the repository path of
               the directory to be copied.
            #. newRelativePath (string): The new directory relative path.
            #. overwrite (boolean): Whether to overwrite existing but not tracked
               directory in repository.
            #. raiseError (boolean): Whether to raise encountered error instead
               of returning failure.
            #. ntrials (int): The maximum number of attempts of the operation once its locks are held.
               Only an error that can pass by itself, such as a busy or interrupted call of the file
               system, is attempted again, after a pause that doubles with every attempt. Any other
               error fails at once, which also keeps your own dump and pull methods from running
               again after they failed. The message of a failure lists the error of every attempt.

        :Returns:
            #. success (boolean): Whether renaming the directory was successful.
            #. message (None, string): Some explanatory message or error reason
               why directory was not renamed.
        """
        if not (isinstance(raiseError, bool)):
            raise Exception("raiseError must be boolean")
        if not (isinstance(overwrite, bool)):
            raise Exception("overwrite must be boolean")
        if not (isinstance(ntrials, int)):
            raise Exception("ntrials must be integer")
        if not (ntrials>0):
            raise Exception("ntrials must be >0")
        relativePath = self.to_repo_relative_path(path=relativePath, split=False)
        if relativePath == '':
            m = "Copying to repository main directory is not possible"
            if raiseError:
                raise Exception(m)
            return False, m
        realPath     = os.path.join(self.__path,relativePath)
        parentRealPath, dirName = os.path.split(realPath)
        if not self.__is_repository_directory(relativePath):
            m = "Directory '%s' is not a tracked repository directory"%(relativePath)
            if raiseError:
                raise Exception(m)
            return False, m
        newRelativePath = self.to_repo_relative_path(path=newRelativePath, split=False)
        newRealPath     = os.path.join(self.__path,newRelativePath)
        newParentRealPath, newDirName = os.path.split(newRealPath)
        newParentRelativePath = os.path.dirname(newRelativePath)
        if newRelativePath == '':
            m = "Copying to repository main directory is not possible"
            if raiseError:
                raise Exception(m)
            return False, m
        if realPath == newRealPath:
            m = "Copying to the same directory is not possible"
            if raiseError:
                raise Exception(m)
            return False, m
        if self.__is_repository_directory(newRelativePath):
            m = "Directory '%s' is a tracked repository directory"%(newRelativePath)
            if raiseError:
                raise Exception(m)
            return False, m
        if os.path.isdir(newRealPath):
            if overwrite:
                try:
                    shutil.rmtree(newRealPath)
                except Exception as err:
                    if raiseError:
                        raise Exception(str(err))
                    return False, str(err)
            else:
                error = "New directory path '%s' already exist on disk. Set overwrite to True"%(newRealPath,)
                if raiseError:
                    raise Exception(error)
                return False, error
        # add directory
        try:
            success, reason = self.add_directory(newParentRelativePath, raiseError=False, ntrials=ntrials)
        except Exception as err:
            reason  = "Unable to add directory (%s)"%(str(err))
            success = False
        if not success:
            if raiseError:
                raise Exception(reason)
            return False, reason
        # lock repository
        acquired, repoLockId = self.__acquire_lock(self.__path)
        if not acquired:
            m = "code %s. Unable to acquire the repository lock. You may try again!"%(repoLockId,)
            if raiseError:
                raise Exception(m)
            return False,m
        try:
            repo = self.__load_repository_pickle_file(os.path.join(self.__path, self.__repoFile))
            self.__repo['walk_repo'] = repo['walk_repo']
        except Exception as err:
            self.__locker.release_lock(repoLockId)
            error = "Unable to load repository info (%s)"%(str(err),)
            if raiseError:
                raise Exception(error)
            return False, error
        # create locks
        if parentRealPath != self.__path:
            acquired, dirLockId = self.__acquire_lock(parentRealPath)
            if not acquired:
                self.__locker.release_lock(repoLockId)
                error = "Code %s. Unable to acquire the lock when adding '%s'. All prior directories were added. You may try again, to finish adding directory"%(dirLockId,parentRealPath)
                if raiseError:
                    raise Exception(error)
                return False, error
        else:
            dirLockId = None
        newDirLockId = None
        if parentRealPath != newParentRealPath and newParentRealPath != self.__path:
            acquired, newDirLockId = self.__acquire_lock(newParentRealPath)
            if not acquired:
                if dirLockId is not None: self.__locker.release_lock(dirLockId)
                self.__locker.release_lock(repoLockId)
                error = "Code %s. Unable to acquire the lock when adding '%s'. All prior directories were added. You may try again, to finish adding directory"%(newDirLockId,newParentRealPath)
                if raiseError:
                    raise Exception(error)
                return False, error
        # get directory parent list
        error = None
        attempts = []
        for _trial in range(ntrials):
            try:
                # make sure again because sometimes, when multiple processes are working on the same repo things can happen in between
                if not (self.__is_repository_directory(relativePath)):
                    raise Exception("Directory '%s' is not anymore a tracked repository directory"%(relativePath))
                if not (not self.__is_repository_directory(newRelativePath)):
                    raise Exception("Directory '%s' has become a tracked repository directory"%(newRelativePath))
                dirList = self.__get_repository_parent_directory(relativePath=relativePath)
                if not (dirList is not None):
                    raise Exception("Given relative path '%s' is not a repository directory"%(relativePath,))
                newDirList = self.__get_repository_parent_directory(relativePath=newRelativePath)
                if not (newDirList is not None):
                    raise Exception("Given new relative path '%s' parent directory is not a repository directory"%(newRelativePath,))
                # change dirName in dirList
                _dirDict = [nd for nd in dirList  if isinstance(nd,dict)]
                _dirDict = [nd for nd in _dirDict if dirName in nd]
                if not (len(_dirDict) == 1):
                    raise Exception("This should not have happened. Directory not found in repository. Please report issue")
                _dirDict = _dirDict[0]
                _newDirDict = [nd for nd in newDirList  if isinstance(nd,dict)]
                _newDirDict = [nd for nd in _newDirDict if newDirName in nd]
                if not (len(_newDirDict) == 0):
                    raise Exception("This should not have happened. New directory is found in repository. Please report issue")
                # try to copy directory
                _newDirDict = copy.deepcopy(_dirDict)
                if dirName != newDirName:
                    _newDirDict[newDirName] = _newDirDict.pop(dirName)
                _ = copy_tree(src=realPath, dst=newRealPath, srcDirDict=_dirDict,
                              filAttr = [self.__fileInfo,self.__fileClass],
                              dirAttr = [self.__dirInfo,self.__repoFile])
                # update newDirList
                newDirList.append(_newDirDict)
                # update and dump dirinfo
                self.__save_dirinfo(description=None, dirInfoPath=newParentRelativePath, create=False)
            except Exception as err:
                error = str(err)
                if self.DEBUG_PRINT_FAILED_TRIALS: print("Trial %i failed in Repository.%s (%s). Set Repository.DEBUG_PRINT_FAILED_TRIALS to False to mute"%(_trial, inspect.stack()[1][3], str(error)))
                attempts.append(error)
                error = describe_attempts(attempts)
                if not should_retry(err, _trial, ntrials):
                    break
            else:
                error = None
                break
        if error is None:
            _, error = self.__save_repository_pickle_file(lockFirst=False, raiseError=False)
        if dirLockId is not None: self.__locker.release_lock(dirLockId)
        self.__locker.release_lock(repoLockId)
        if newDirLockId is not None: self.__locker.release_lock(newDirLockId)
        # check and return
        if error is not None and raiseError:
            raise Exception("Unable to copy directory '%s' to '%s' after %i trials (%s)"%(relativePath, newRelativePath, ntrials, error,))
        return error is None, error


    @path_required
    def dump_file(self, value, relativePath,
                        description=None,
                        dump=None, pull=None,
                        replace=False, raiseError=True, ntrials=3):
        """
        Dump a file using its value to the system and creates its
        attribute in the Repository with utc timestamp.

        :Parameters:
            #. value (object): The value of a file to dump and add to the
               repository. It is any python object or file.
            #. relativePath (str): The relative to the repository path to where
               to dump the file.
            #. description (None, string): Any description about the file.
            #. dump (None, string): The dumping method. None uses pickle. A string
               is either a keyword ('pickle', 'dill', 'json', 'numpy' or
               'numpy_text', where 'pickle' and 'dill' accept a protocol such as
               'pickle2') or source code that defines a function `dump(path, value)`
               that writes value to path and imports whatever it needs.\n
               e.g. "import numpy as np; dump=lambda path,value:np.savetxt(fname=path, X=value, fmt='%.6e')"
            #. pull (None, string): The pulling method. None uses pickle, or the
               same keyword as dump when dump is a keyword. A string is either a
               keyword, as for dump, or source code that defines a function
               `pull(path)` that returns the data and imports whatever it needs.\n
               e.g. "import numpy as np; pull=lambda path:np.loadtxt(fname=path)"
            #. replace (boolean): Whether to replace any existing file.
            #. raiseError (boolean): Whether to raise encountered error instead
               of returning failure.
            #. ntrials (int): The maximum number of attempts of the operation once its locks are held.
               Only an error that can pass by itself, such as a busy or interrupted call of the file
               system, is attempted again, after a pause that doubles with every attempt. Any other
               error fails at once, which also keeps your own dump and pull methods from running
               again after they failed. The message of a failure lists the error of every attempt.

        :Returns:
            #. success (boolean): Whether renaming the directory was successful.
            #. message (None, string): Some explanatory message or error reason
               why directory was not dumped.
        """
        # check arguments
        if not (isinstance(raiseError, bool)):
            raise Exception("raiseError must be boolean")
        if not (isinstance(replace, bool)):
            raise Exception("replace must be boolean")
        if not (isinstance(ntrials, int)):
            raise Exception("ntrials must be integer")
        if not (ntrials>0):
            raise Exception("ntrials must be >0")
        if description is None:
            description = ''
        if not (isinstance(description, str)):
            raise Exception("description must be None or a string")
        # convert dump and pull methods to strings
        if pull is None and dump is not None:
            if dump.startswith('pickle') or dump.startswith('dill') or dump.startswith('numpy') or dump =='json':
                pull = dump
        dump = get_dump_method(dump, protocol=self._DEFAULT_PICKLE_PROTOCOL)
        pull = get_pull_method(pull)
        # check name and path
        relativePath = self.to_repo_relative_path(path=relativePath, split=False)
        savePath     = os.path.join(self.__path,relativePath)
        fPath, fName = os.path.split(savePath)
        # check if name is allowed
        success, reason = self.is_name_allowed(savePath)
        if not success:
            if raiseError:
                raise Exception(reason)
            return False, reason
        # ensure directory added
        try:
            success, reason = self.add_directory(fPath, raiseError=False, ntrials=ntrials)
        except Exception as err:
            reason  = "Unable to add directory (%s)"%(str(err))
            success = False
        if not success:
            if raiseError:
                raise Exception(reason)
            return False, reason
        # lock repository
        acquired, repoLockId = self.__acquire_lock(self.__path)
        if not acquired:
            m = "code %s. Unable to acquire the repository lock. You may try again!"%(repoLockId,)
            if raiseError:
                raise Exception(m)
            return False,m
        # lock file
        acquired, fileLockId = self.__acquire_file_lock(savePath)
        if not acquired:
            self.__locker.release_lock(repoLockId)
            error = "Code %s. Unable to acquire the lock when dumping '%s'"%(fileLockId,relativePath)
            if raiseError:
                raise Exception(error)
            return False, error
        # load repository info
        attempts = []
        for _trial in range(ntrials):
            try:
                repo = self.__load_repository_pickle_file(os.path.join(self.__path, self.__repoFile))
                self.__repo['walk_repo'] = repo['walk_repo']
            except Exception as err:
                error = str(err)
                if self.DEBUG_PRINT_FAILED_TRIALS: print("Trial %i failed in Repository.%s (%s). Set Repository.DEBUG_PRINT_FAILED_TRIALS to False to mute"%(_trial, inspect.stack()[1][3], str(error)))
                attempts.append(error)
                error = describe_attempts(attempts)
                if not should_retry(err, _trial, ntrials):
                    break
            else:
                error = None
                break
        if error is not None:
            self.__locker.release_lock(fileLockId)
            self.__locker.release_lock(repoLockId)
            if raiseError:
                raise Exception(error)
            return False, error
        # dump file
        attempts = []
        for _trial in range(ntrials):
            error = None
            try:
                isRepoFile, fileOnDisk, _, _ = self.__is_repository_file(relativePath)
                if isRepoFile:
                    if not (replace):
                        raise Exception("file is a registered repository file. set replace to True to replace")
                fileInfoPath = os.path.join(self.__path,os.path.dirname(relativePath),self.__fileInfo%fName)
                if isRepoFile and fileOnDisk:
                    with open(fileInfoPath, 'rb') as fd:
                        info = pickle.load(fd)
                    if not (info['repository_unique_name'] == self.__repo['repository_unique_name']):
                        raise Exception("it seems that file was created by another repository")
                    info['last_update_utctime'] = time.time()
                else:
                    info = {'repository_unique_name':self.__repo['repository_unique_name']}
                    info['create_utctime'] = info['last_update_utctime'] = time.time()
                info['dump'] = dump
                info['pull'] = pull
                info['description'] = description
                # get parent directory list if file is new and not being replaced
                if not isRepoFile:
                    dirList = self.__get_repository_directory(fPath)
                # dump file
                dumpFunc = my_exec( dump, name='dump', description='dump')
                fileClassPath = os.path.join(self.__path,os.path.dirname(relativePath),self.__fileClass%fName)
                # the data, info and class files are all written completely before any of them replaces the old one
                write_files_together(dumpFunc, str(savePath), value,
                                     [(fileInfoPath, info), (fileClassPath, get_class_name(value))],
                                     self._DEFAULT_PICKLE_PROTOCOL, os.path.join(fPath, self.__fileJournal%fName))
                # add to repo if file is new and not being replaced
                if not isRepoFile:
                    dirList.append(fName)
            except Exception as err:
                error = "unable to dump the file (%s)"%(str(err),)
                try:
                    if 'pickle.dump(' in dump:
                        mi = get_pickling_errors(value)
                        if mi is not None:
                            error += '\nmore info: %s'%str(mi)
                except Exception:
                    pass
                if self.DEBUG_PRINT_FAILED_TRIALS: print("Trial %i failed in Repository.%s (%s). Set Repository.DEBUG_PRINT_FAILED_TRIALS to False to mute"%(_trial, inspect.stack()[1][3], str(error)))
                attempts.append(error)
                error = describe_attempts(attempts)
                if not should_retry(err, _trial, ntrials):
                    break
            else:
                error = None
                break
        # save repository
        if error is None:
            _, error = self.__save_repository_pickle_file(lockFirst=False, raiseError=False)
        # release locks
        self.__locker.release_lock(fileLockId)
        self.__locker.release_lock(repoLockId)
        # check and return
        if error is not None and raiseError:
            raise Exception("unable to dump file '%s' after %i trials (%s)"%(relativePath, ntrials, error,))
        return error is None, error

    def dump(self, *args, **kwargs):
        """Alias to dump_file"""
        return self.dump_file(*args, **kwargs)


    @path_required
    def copy_file(self, relativePath, newRelativePath,
                        force=False, raiseError=True, ntrials=3):
        """
        Copy a file in the repository.

        :Parameters:
            #. relativePath (string): The relative to the repository path of
               the file that needst to be renamed.
            #. newRelativePath (string): The new relative to the repository path
               of where to move and rename the file.
            #. force (boolean): Whether to force renaming even when another
               repository file exists. In this case old repository file
               will be removed from the repository and the system as well.
            #. raiseError (boolean): Whether to raise encountered error instead
               of returning failure.
            #. ntrials (int): The maximum number of attempts of the operation once its locks are held.
               Only an error that can pass by itself, such as a busy or interrupted call of the file
               system, is attempted again, after a pause that doubles with every attempt. Any other
               error fails at once, which also keeps your own dump and pull methods from running
               again after they failed. The message of a failure lists the error of every attempt.

        :Returns:
            #. success (boolean): Whether renaming the file was successful.
            #. message (None, string): Some explanatory message or error reason
               why directory was not updated.
        """
        if not (isinstance(raiseError, bool)):
            raise Exception("raiseError must be boolean")
        if not (isinstance(force, bool)):
            raise Exception("force must be boolean")
        if not (isinstance(ntrials, int)):
            raise Exception("ntrials must be integer")
        if not (ntrials>0):
            raise Exception("ntrials must be >0")
        # check old name and path
        relativePath = self.to_repo_relative_path(path=relativePath, split=False)
        realPath     = os.path.join(self.__path,relativePath)
        fPath, fName = os.path.split(realPath)
        # check new name and path
        newRelativePath = self.to_repo_relative_path(path=newRelativePath, split=False)
        newRealPath     = os.path.join(self.__path,newRelativePath)
        nfPath, nfName  = os.path.split(newRealPath)
        refusal = self.__root_refusal(raiseError, relativePath, newRelativePath)
        if refusal is not None:
            return refusal
        if realPath == newRealPath:
            error = "Copying a file onto itself is not possible"
            if raiseError:
                raise Exception(error)
            return False, error
        # add new file directory
        try:
            success, reason = self.add_directory(nfPath, raiseError=False, ntrials=ntrials)
        except Exception as err:
            reason  = "Unable to add directory (%s)"%(str(err))
            success = False
        if not success:
            if raiseError:
                raise Exception(reason)
            return False, reason
        # lock repository
        acquired, repoLockId = self.__acquire_lock(self.__path)
        if not acquired:
            error = "Code %s. Unable to acquire the repository lock when copying '%s'. You may try again!"%(repoLockId, relativePath)
            if raiseError:
                raise Exception(error)
            return False, error
        # lock old file
        acquired, fileLockId = self.__acquire_file_lock(realPath)
        if not acquired:
            self.__locker.release_lock(repoLockId)
            error = "Code %s. Unable to acquire the lock for old file '%s'. You may try again!"%(fileLockId, relativePath)
            if raiseError:
                raise Exception(error)
            return False, error
        # lock new file
        acquired, newFileLockId = self.__acquire_file_lock(newRealPath)
        if not acquired:
            self.__locker.release_lock(fileLockId)
            self.__locker.release_lock(repoLockId)
            error = "Code %s. Unable to acquire the lock for new file path '%s'. You may try again!"%(newFileLockId, newRelativePath)
            if raiseError:
                raise Exception(error)
            return False, error
        # copy file
        attempts = []
        for _trial in range(ntrials):
            copied = False
            error  = None
            try:
                # Reload because another process may have changed the tracked files since the last read
                repo = self.__load_repository_pickle_file(os.path.join(self.__path, self.__repoFile))
                self.__repo['walk_repo'] = repo['walk_repo']
                # check whether it's a repository file
                isRepoFile,fileOnDisk, infoOnDisk, classOnDisk = self.__is_repository_file(relativePath)
                if not (isRepoFile):
                    raise Exception("file '%s' is not a repository file"%(relativePath,))
                if not (fileOnDisk):
                    raise Exception("file '%s' is not found on disk"%(relativePath,))
                if not (infoOnDisk):
                    raise Exception("%s is not found on disk"%(self.__fileInfo%fName,))
                if not (classOnDisk):
                    raise Exception("%s is not found on disk"%(self.__fileClass%fName,))
                # get new file path
                nisRepoFile, _, _, _ = self.__is_repository_file(newRelativePath)
                if not (not nisRepoFile or force):
                    raise Exception("New file path is a registered repository file, set force to True to proceed regardless")
                # get parent directories list
                nDirList = self.__get_repository_directory(nfPath)
                # copy the file to the new path, replacing what is there in one step
                copy_files_together([(realPath, newRealPath),
                                     (os.path.join(fPath,self.__fileInfo%fName),  os.path.join(nfPath,self.__fileInfo%nfName)),
                                     (os.path.join(fPath,self.__fileClass%fName), os.path.join(nfPath,self.__fileClass%nfName))],
                                    os.path.join(nfPath,self.__fileJournal%nfName), self._DEFAULT_PICKLE_PROTOCOL)
                # update new list
                if nfName not in nDirList:
                    nDirList.append(nfName)
            except Exception as err:
                copied = False
                error = str(err)
                if self.DEBUG_PRINT_FAILED_TRIALS: print("Trial %i failed in Repository.%s (%s). Set Repository.DEBUG_PRINT_FAILED_TRIALS to False to mute"%(_trial, inspect.stack()[1][3], str(error)))
                attempts.append(error)
                error = describe_attempts(attempts)
                if not should_retry(err, _trial, ntrials):
                    break
            else:
                error = None
                copied = True
                break
        # save repository
        if copied:
            saved, saveError = self.__save_repository_pickle_file(lockFirst=False, raiseError=False)
            if not saved:
                copied = False
                error  = saveError
        # release locks
        self.__locker.release_lock(fileLockId)
        self.__locker.release_lock(newFileLockId)
        self.__locker.release_lock(repoLockId)
        # check and return
        if not copied and raiseError:
            raise Exception("Unable to copy file '%s' to '%s' after %i trials (%s)"%(relativePath, newRelativePath, ntrials, error,))
        return copied, error


    @path_required
    def update_file(self, value, relativePath, description=False,
                          dump=False, pull=False, raiseError=True, ntrials=3):
        """
        Update the value of a file that is already in the Repository.\n
        If file is not registered in repository, and error will be thrown.\n
        If file is missing in the system, it will be regenerated as dump method
        is called.
        Unlike dump_file, update_file won't block the whole repository but only
        the file being updated.

        :Parameters:
            #. value (object): The value of a file to update.
            #. relativePath (str): The relative to the repository path of the
               file to be updated.
            #. description (False, string): Any random description about the file.
               If False is given, the description info won't be updated,
               otherwise it will be update to what description argument value is.
            #. dump (False, string): The new dump method. If False is given,
               the old one will be used.
            #. pull (False, string): The new pull method. If False is given,
               the old one will be used.
            #. raiseError (boolean): Whether to raise encountered error instead
               of returning failure.
            #. ntrials (int): The maximum number of attempts of the operation once its locks are held.
               Only an error that can pass by itself, such as a busy or interrupted call of the file
               system, is attempted again, after a pause that doubles with every attempt. Any other
               error fails at once, which also keeps your own dump and pull methods from running
               again after they failed. The message of a failure lists the error of every attempt.

       :Returns:
           #. success (boolean): Whether renaming the directory was successful.
           #. message (None, string): Some explanatory message or error reason
              why directory was not updated.
        """
        # check arguments
        if not (isinstance(raiseError, bool)):
            raise Exception("raiseError must be boolean")
        if not (description is False or description is None or isinstance(description, str)):
            raise Exception("description must be False, None or a string")
        if not (dump is False or dump is None or isinstance(dump, str)):
            raise Exception("dump must be False, None or a string")
        if not (pull is False or pull is None or isinstance(pull, str)):
            raise Exception("pull must be False, None or a string")
        if not (isinstance(ntrials, int)):
            raise Exception("ntrials must be integer")
        if not (ntrials>0):
            raise Exception("ntrials must be >0")
        self.__complete_repository_journal()
        # get name and path
        relativePath = self.to_repo_relative_path(path=relativePath, split=False)
        savePath     = os.path.join(self.__path,relativePath)
        fPath, fName = os.path.split(savePath)
        # get locker
        acquired, fileLockId = self.__acquire_file_lock(savePath)
        if not acquired:
            error = "Code %s. Unable to acquire the lock to update '%s'"%(fileLockId,relativePath)
            if raiseError:
                raise Exception(error)
            return False, error
        # update file
        attempts = []
        for _trial in range(ntrials):
            message = []
            updated = False
            try:
                # check file in repository
                isRepoFile, fileOnDisk, infoOnDisk, classOnDisk = self.__is_repository_file(relativePath)
                if not (isRepoFile):
                    raise Exception("file '%s' is not registered in repository, no update can be performed."%(relativePath,))
                # get file info
                if not fileOnDisk:
                    if not (description is not False):
                        raise Exception("file '%s' is not found on disk, description must be provided"%(relativePath,))
                    if not (dump is not False):
                        raise Exception("file '%s' is not found on disk, dump must be provided"%(relativePath,))
                    if not (pull is not False):
                        raise Exception("file '%s' is not found on disk, pull must be provided"%(relativePath,))
                    info = {}
                    info['repository_unique_name'] = self.__repo['repository_unique_name']
                    info['create_utctime'] = info['last_update_utctime'] = time.time()
                else:
                    with open(os.path.join(fPath,self.__fileInfo%fName), 'rb') as fd:
                        info = pickle.load(fd)
                        info['last_update_utctime'] = time.time()
                if not fileOnDisk:
                    message.append("file %s is registered in repository but it was not found on disk prior to updating"%relativePath)
                if not infoOnDisk:
                    message.append("%s is not found on disk prior to updating"%(self.__fileInfo%fName,))
                if not classOnDisk:
                    message.append("%s is not found on disk prior to updating"%(self.__fileClass%fName,))
                # get dump and pull
                if description is False:
                    description = info['description']
                elif description is None:
                    description = ''
                if dump is False:
                    dump = info['dump']
                else:
                    dump = get_dump_method(dump, protocol=self._DEFAULT_PICKLE_PROTOCOL)
                if pull is False:
                    pull = info['pull']
                else:
                    pull = get_pull_method(pull)
                # update dump, pull and description
                info['dump'] = dump
                info['pull'] = pull
                info['description'] = description
                # dump file
                dumpFunc = my_exec( dump, name='dump', description='update')
                _path = os.path.join(fPath,self.__fileInfo%fName)
                fileClassPath = os.path.join(self.__path,os.path.dirname(relativePath),self.__fileClass%fName)
                # the data, info and class files are all written completely before any of them replaces the old one
                write_files_together(dumpFunc, str(savePath), value,
                                     [(_path, info), (fileClassPath, get_class_name(value))],
                                     self._DEFAULT_PICKLE_PROTOCOL, os.path.join(fPath, self.__fileJournal%fName))
            except Exception as err:
                message.append(str(err))
                updated = False
                try:
                    if 'pickle.dump(' in dump:
                        mi = get_pickling_errors(value)
                        if mi is not None:
                            message.append('more info: %s'%str(mi))
                except Exception:
                    pass
                if self.DEBUG_PRINT_FAILED_TRIALS: print("Trial %i failed in Repository.%s (%s). Set Repository.DEBUG_PRINT_FAILED_TRIALS to False to mute"%(_trial, inspect.stack()[1][3], '\n'.join(message)))
                attempts.append('; '.join(message))
                message[:] = [describe_attempts(attempts)]
                if not should_retry(err, _trial, ntrials):
                    break
            else:
                updated = True
                break
        # release lock
        self.__locker.release_lock(fileLockId)
        # check and return
        if not updated and raiseError:
            raise Exception("Unable to update file '%s' (%s)"%(relativePath, '\n'.join(message),))
        return updated, '\n'.join(message)

    def update(self, *args, **kwargs):
        """Alias to update_file"""
        return self.update_file(*args, **kwargs)


    @path_required
    def pull_file(self, relativePath, pull=None, ntrials=3):
        """
        Pulls a file's data from the repository.

        :Parameters:
            #. relativePath (string): The relative to the repository path from
               where to pull the file.
            #. pull (None, string): The pulling method. If None, the method saved
               in the file info is used. Otherwise it is a keyword ('pickle',
               'dill', 'json', 'numpy' or 'numpy_text') or source code that defines
               a function `pull(path)` that returns the data.
            #. ntrials (int): The maximum number of attempts of the operation once its locks are held.
               Only an error that can pass by itself, such as a busy or interrupted call of the file
               system, is attempted again, after a pause that doubles with every attempt. Any other
               error fails at once, which also keeps your own dump and pull methods from running
               again after they failed. The message of a failure lists the error of every attempt.

        :Returns:
            #. data (object): The pulled data from the file.

        :Raises:
            #. Exception: If the file is not a repository file, is missing on disk,
               its lock cannot be acquired or pulling fails after ntrials trials.
        """
        if not (isinstance(ntrials, int)):
            raise Exception("ntrials must be integer")
        if not (ntrials>0):
            raise Exception("ntrials must be >0")
        self.__complete_repository_journal()
        # check name and path
        relativePath = self.to_repo_relative_path(path=relativePath, split=False)
        realPath     = os.path.join(self.__path,relativePath)
        fPath, fName = os.path.split(realPath)
        # check whether it's a repository file
        isRepoFile,fileOnDisk, infoOnDisk, classOnDisk = self.is_repository_file(relativePath)
        if not isRepoFile:
            fileOnDisk  = ["",". File itself is found on disk"][fileOnDisk]
            infoOnDisk  = ["",". %s is found on disk"%(self.__fileInfo%fName,)][infoOnDisk]
            classOnDisk = ["",". %s is found on disk"%(self.__fileClass%fName,)][classOnDisk]
            raise Exception("File '%s' is not a repository file%s%s%s"%(relativePath,fileOnDisk,infoOnDisk,classOnDisk))
        if not fileOnDisk:
            raise Exception("File '%s' is registered in repository but the file itself was not found on disk"%(relativePath,))
        if not infoOnDisk:
            if pull is not None:
                warnings.warn("'%s' was not found on disk but pull method is given"%(self.__fileInfo%fName))
            else:
                raise Exception("File '%s' is registered in repository but the '%s' was not found on disk and pull method is not specified"%(relativePath,(self.__fileInfo%fName)))
        # lock file
        acquired, fileLockId = self.__acquire_file_lock(realPath)
        if not acquired:
            raise Exception("Code %s. Unable to acquire the lock when pulling '%s'"%(fileLockId,relativePath))
        # pull file, the lock is released once whatever happens
        try:
            givenCode = None if pull is None else get_pull_method(pull)
            attempts = []
            for _trial in range(ntrials):
                error = None
                pullCode = givenCode
                try:
                    if pullCode is None:
                        with open(os.path.join(fPath,self.__fileInfo%fName), 'rb') as fd:
                            pullCode = pickle.load(fd)['pull']
                    pullFunc  = my_exec( pullCode, name='pull', description='pull')
                    pulledVal = pullFunc(path=str(realPath))
                except Exception as err:
                    error = "Unable to pull data using '%s' from file (%s)"%(pullCode, err)
                    if self.DEBUG_PRINT_FAILED_TRIALS: print("Trial %i failed in Repository.%s (%s). Set Repository.DEBUG_PRINT_FAILED_TRIALS to False to mute"%(_trial, inspect.stack()[1][3], str(error)))
                    attempts.append(error)
                    error = describe_attempts(attempts)
                    if not should_retry(err, _trial, ntrials):
                        break
                else:
                    break
        finally:
            self.__locker.release_lock(fileLockId)
        # check and return
        if error is not None:
            raise Exception("After %i trials, failed to pull file '%s' (%s)"%(ntrials,relativePath, error))
        return pulledVal

    def pull(self, *args, **kwargs):
        """Alias to pull_file"""
        return self.pull_file(*args, **kwargs)


    @path_required
    def rename_file(self, relativePath, newRelativePath,
                          force=False, raiseError=True, ntrials=3):
        """
        Rename a file in the repository. It insures renaming the file in the system.

        :Parameters:
            #. relativePath (string): The relative to the repository path of
               the file that needst to be renamed.
            #. newRelativePath (string): The new relative to the repository path
               of where to move and rename the file.
            #. force (boolean): Whether to force renaming even when another
               repository file exists. In this case old repository file
               will be removed from the repository and the system as well.
            #. raiseError (boolean): Whether to raise encountered error instead
               of returning failure.
            #. ntrials (int): The maximum number of attempts of the operation once its locks are held.
               Only an error that can pass by itself, such as a busy or interrupted call of the file
               system, is attempted again, after a pause that doubles with every attempt. Any other
               error fails at once, which also keeps your own dump and pull methods from running
               again after they failed. The message of a failure lists the error of every attempt.

        :Returns:
            #. success (boolean): Whether renaming the file was successful.
            #. message (None, string): Some explanatory message or error reason
               why directory was not updated.
        """
        if not (isinstance(raiseError, bool)):
            raise Exception("raiseError must be boolean")
        if not (isinstance(force, bool)):
            raise Exception("force must be boolean")
        if not (isinstance(ntrials, int)):
            raise Exception("ntrials must be integer")
        if not (ntrials>0):
            raise Exception("ntrials must be >0")
        # check old name and path
        relativePath = self.to_repo_relative_path(path=relativePath, split=False)
        realPath     = os.path.join(self.__path,relativePath)
        fPath, fName = os.path.split(realPath)
        # check new name and path
        newRelativePath = self.to_repo_relative_path(path=newRelativePath, split=False)
        newRealPath     = os.path.join(self.__path,newRelativePath)
        nfPath, nfName  = os.path.split(newRealPath)
        refusal = self.__root_refusal(raiseError, relativePath, newRelativePath)
        if refusal is not None:
            return refusal
        if realPath == newRealPath:
            error = "Renaming a file onto itself is not possible"
            if raiseError:
                raise Exception(error)
            return False, error
        # add directory
        try:
            success, reason = self.add_directory(nfPath, raiseError=False, ntrials=ntrials)
        except Exception as err:
            reason  = "Unable to add directory (%s)"%(str(err))
            success = False
        if not success:
            if raiseError:
                raise Exception(reason)
            return False, reason
        # lock repository
        acquired, repoLockId = self.__acquire_lock(self.__path)
        if not acquired:
            error = "Code %s. Unable to acquire the repository lock when renaming '%s'. You may try again!"%(repoLockId, relativePath)
            if raiseError:
                raise Exception(error)
            return False, error
        # lock old file
        acquired, fileLockId = self.__acquire_file_lock(realPath)
        if not acquired:
            self.__locker.release_lock(repoLockId)
            error = "Code %s. Unable to acquire the lock for old file '%s'. You may try again!"%(fileLockId, relativePath)
            if raiseError:
                raise Exception(error)
            return False, error
        # lock new file
        acquired, newFileLockId = self.__acquire_file_lock(newRealPath)
        if not acquired:
            self.__locker.release_lock(fileLockId)
            self.__locker.release_lock(repoLockId)
            error = "Code %s. Unable to acquire the lock for new file path '%s'. You may try again!"%(newFileLockId, newRelativePath)
            if raiseError:
                raise Exception(error)
            return False, error
        # rename file
        nisRepoFile = False
        attempts = []
        for _trial in range(ntrials):
            renamed = False
            error   = None
            try:
                # Reload because another process may have changed the tracked files since the last read
                repo = self.__load_repository_pickle_file(os.path.join(self.__path, self.__repoFile))
                self.__repo['walk_repo'] = repo['walk_repo']
                # check whether it's a repository file
                isRepoFile,fileOnDisk, infoOnDisk, classOnDisk = self.__is_repository_file(relativePath)
                if not (isRepoFile):
                    raise Exception("file '%s' is not a repository file"%(relativePath,))
                if not (fileOnDisk):
                    raise Exception("file '%s' is not found on disk"%(relativePath,))
                if not (infoOnDisk):
                    raise Exception("%s is not found on disk"%(self.__fileInfo%fName,))
                if not (classOnDisk):
                    raise Exception("%s is not found on disk"%(self.__fileClass%fName,))
                # get new file path
                nisRepoFile, _, _, _ = self.__is_repository_file(newRelativePath)
                if not (not nisRepoFile or force):
                    raise Exception("New file path is a registered repository file, set force to True to proceed regardless")
                # get parent directories list
                oDirList = self.__get_repository_directory(fPath)
                nDirList = self.__get_repository_directory(nfPath)
                # The new names appear first, all together and linked to the same data. The old names stay until the
                # index is saved, so a crash leaves every tracked file complete and the rename done or not done
                copy_files_together([(realPath, newRealPath),
                                     (os.path.join(fPath,self.__fileInfo%fName),  os.path.join(nfPath,self.__fileInfo%nfName)),
                                     (os.path.join(fPath,self.__fileClass%fName), os.path.join(nfPath,self.__fileClass%nfName))],
                                    os.path.join(nfPath,self.__fileJournal%nfName), self._DEFAULT_PICKLE_PROTOCOL, link=True)
                # update list
                findex = oDirList.index(fName)
                oDirList.pop(findex)
                # update new list
                if nfName not in nDirList:
                    nDirList.append(nfName)
            except Exception as err:
                renamed = False
                error = str(err)
                if self.DEBUG_PRINT_FAILED_TRIALS: print("Trial %i failed in Repository.%s (%s). Set Repository.DEBUG_PRINT_FAILED_TRIALS to False to mute"%(_trial, inspect.stack()[1][3], str(error)))
                attempts.append(error)
                error = describe_attempts(attempts)
                if not should_retry(err, _trial, ntrials):
                    break
            else:
                renamed = True
                break
        # save repository, which is the commit point of the rename
        newNames = [newRealPath, os.path.join(nfPath,self.__fileInfo%nfName), os.path.join(nfPath,self.__fileClass%nfName)]
        if renamed:
            saved, saveError = self.__save_repository_pickle_file(lockFirst=False, raiseError=False)
            if saved:
                self.__remove_files([realPath, os.path.join(fPath,self.__fileInfo%fName), os.path.join(fPath,self.__fileClass%fName)])
            else:
                renamed = False
                error   = saveError
                self.__resync_index()
        # A rename that did not happen must not leave new names behind, unless they were tracked before it
        if not renamed and not nisRepoFile:
            self.__remove_files(newNames)
        # release locks
        self.__locker.release_lock(fileLockId)
        self.__locker.release_lock(newFileLockId)
        self.__locker.release_lock(repoLockId)
        # always clean old file lock
        try:
            if os.path.isfile(os.path.join(fPath,self.__fileLock%fName)):
                os.remove(os.path.join(fPath,self.__fileLock%fName))
        except OSError:
            pass
        # check and return
        if not renamed and raiseError:
            raise Exception("Unable to rename file '%s' to '%s' after %i trials (%s)"%(relativePath, newRelativePath, ntrials, error,))
        return renamed, error


    @path_required
    def remove_file(self, relativePath, raiseError=True, ntrials=3):
        """
        Remove a file from the repository and from disk.

        :Parameters:
            #. relativePath (string): The relative to the repository path of the
               file to remove.
            #. raiseError (boolean): Whether to raise encountered error instead
               of returning failure.
            #. ntrials (int): The maximum number of attempts of the operation once its locks are held.
               Only an error that can pass by itself, such as a busy or interrupted call of the file
               system, is attempted again, after a pause that doubles with every attempt. Any other
               error fails at once, which also keeps your own dump and pull methods from running
               again after they failed. The message of a failure lists the error of every attempt.

        :Returns:
            #. removed (boolean): Whether removing the file was successful.
            #. message (str): Explanatory message or error reason. Empty on success.
        """
        if not (isinstance(raiseError, bool)):
            raise Exception("raiseError must be boolean")
        if not (isinstance(ntrials, int)):
            raise Exception("ntrials must be integer")
        if not (ntrials>0):
            raise Exception("ntrials must be >0")
        # check name and path
        relativePath = self.to_repo_relative_path(path=relativePath, split=False)
        realPath     = os.path.join(self.__path,relativePath)
        fPath, fName = os.path.split(realPath)
        refusal = self.__root_refusal(raiseError, relativePath)
        if refusal is not None:
            return refusal
        # lock repository
        acquired, repoLockId = self.__acquire_lock(self.__path)
        if not acquired:
            error = "Code %s. Unable to acquire the repository lock when removing '%s'. You may try again!"%(repoLockId, relativePath)
            if raiseError:
                raise Exception(error)
            return False, error
        # lock file
        acquired, fileLockId = self.__acquire_file_lock(realPath)
        if not acquired:
            self.__locker.release_lock(repoLockId)
            error = "Code %s. Unable to acquire the file lock when removing '%s'. You may try again!"%(fileLockId, relativePath)
            if raiseError:
                raise Exception(error)
            return False, error
        # remove file
        attempts = []
        for _trial in range(ntrials):
            removed = False
            message = []
            try:
                # Reload because another process may have changed the tracked files since the last read
                repo = self.__load_repository_pickle_file(os.path.join(self.__path, self.__repoFile))
                self.__repo['walk_repo'] = repo['walk_repo']
                # check whether it's a repository file
                isRepoFile,fileOnDisk, infoOnDisk, classOnDisk = self.__is_repository_file(relativePath)
                if not isRepoFile:
                    details = ["File '%s' is not a repository file"%(relativePath,)]
                    if fileOnDisk:
                        details.append("File itself is found on disk")
                    if infoOnDisk:
                        details.append("%s is not found on disk"%(self.__fileInfo%fName,))
                    if classOnDisk:
                        details.append("%s is not found on disk"%(self.__fileClass%fName,))
                    raise Exception("; ".join(details))
                else:
                    dirList = self.__get_repository_directory(fPath)
                    findex  = dirList.index(fName)
                    dirList.pop(findex)
            except Exception as err:
                removed = False
                message.append(str(err))
                if self.DEBUG_PRINT_FAILED_TRIALS: print("Trial %i failed in Repository.%s (%s). Set Repository.DEBUG_PRINT_FAILED_TRIALS to False to mute"%(_trial, inspect.stack()[1][3], '\n'.join(message)))
                attempts.append('; '.join(message))
                message[:] = [describe_attempts(attempts)]
                if not should_retry(err, _trial, ntrials):
                    break
            else:
                removed = True
                break
        # save repository, which is the commit point, and only then delete the files, so that a crash never leaves
        # a tracked file without its data
        if removed:
            saved, saveError = self.__save_repository_pickle_file(lockFirst=False, raiseError=False)
            if saved:
                failed = self.__remove_files([realPath, os.path.join(fPath,self.__fileInfo%fName), os.path.join(fPath,self.__fileClass%fName)])
                if len(failed):
                    message.append("The file is removed from the repository but could not be deleted from disk: %s"%("; ".join(failed),))
            else:
                removed = False
                message.append(saveError)
                self.__resync_index()
        # release locks
        self.__locker.release_lock(fileLockId)
        self.__locker.release_lock(repoLockId)
        # always clean
        try:
            if os.path.isfile(os.path.join(fPath,self.__fileLock%fName)):
                os.remove(os.path.join(fPath,self.__fileLock%fName))
        except OSError:
            pass
        # check and return
        if not removed and raiseError:
            raise Exception("Unable to remove file '%s' after %i trials (%s)"%(relativePath, ntrials, '\n'.join(message),))
        return removed, '\n'.join(message)
