"""
Usage:
======

.. code-block:: python

    from __future__ import print_function
    import os
    import warnings
    from pprint import pprint

    # numpy imports
    import numpy as np

    # import Repository
    from pyrep import Repository

    # initialize Repository instance
    REP=Repository()

    # create a path pointing to user home
    PATH = os.path.join(os.path.expanduser("~"), 'pyrepTest_canBeDeleted')

    # check if directory exist
    if REP.is_repository(PATH):
        REP.remove_repository(path=PATH, removeEmptyDirs=True)


    # print repository path
    print("repository path --> %s"%str(REP.path))

    # create repository in path
    print("\\n\\nIs path '%s' a repository --> %s"%(PATH, str(REP.is_repository(PATH))))
    success,message = REP.create_repository(PATH)
    assert success, message
    print('\\nRepository path --> %s'%str(REP.path))

    # add directories
    success,message = REP.add_directory("folder1/folder2/folder3")
    if not success:
        print(message)

    success,message = REP.add_directory("folder1/archive1/archive2/archive3/archive3")
    if not success:
        print(message)

    success,message = REP.add_directory("directory1/directory2")
    if not success:
        print(message)

    # dump files
    value = "This is a string data to pickle and store in the repository"
    success,message = REP.dump_file(value, relativePath='pickled', dump=None, pull=None, replace=True)
    if not success:
        print(message)

    value = np.random.random(3)
    dump  = "import numpy as np; dump=lambda path,value:np.savetxt(fname=path, X=value, fmt='%.6e')"
    pull  = "import numpy as np; pull=lambda path:np.loadtxt(fname=path)"

    success,message = REP.dump(value, relativePath='text.dat', dump=dump, pull=pull, replace=True)
    if not success:
        print(message)

    success,message = REP.dump(value, relativePath="folder1/folder2/folder3/folder3Pickled.pkl", replace=True)
    if not success:
        print(message)

    success,message = REP.dump(value, relativePath="folder1/archive1/archive1Pickled1", replace=True)
    if not success:
        print(message)

    success,message = REP.dump(value, relativePath="folder1/archive1/archive1Pickled2", replace=True)
    if not success:
        print(message)

    success,message = REP.dump(value, relativePath="folder1/archive1/archive2/archive2Pickled1", replace=True)
    if not success:
        print(message)

    # pull data
    data = REP.pull(relativePath='text.dat')
    print('\\n\\nPulled text data --> %s'%str(data))


    data = REP.pull(relativePath="folder1/folder2/folder3/folder3Pickled.pkl")
    print('\\n\\nPulled pickled data --> %s'%str(data))


    # update
    value = "This is an updated string"
    REP.update(value, relativePath='pickled')
    print('\\nUpdate pickled data to --> %s'%value)

    # walk repository files
    print('\\n\\nwalk repository files relative path')
    print('------------------------------------')
    for f in REP.walk_files_path(recursive=True):
        print(f)


    # walk repository, directories
    print('\\n\\nwalk repository directories relative path')
    print('------------------------------------------')
    for d in REP.walk_directories_path(recursive=True):
        print(d)


    print('\\n\\nRepository print -->')
    print(REP)


    print('\\n\\nRepository representation -->')
    print(repr(REP))


    print('\\n\\nRepository to list -->')
    for fdDict in REP.get_repository_state():
        k = list(fdDict)[0]
        print("%s: %s"%(k,str(fdDict[k])))


    print('\\n\\nCreate package from repository ...')
    REP.create_package(path=None, name=None)

    # Try to load
    try:
        REP.load_repository(PATH)
    except:
        loadable = False
    finally:
        loadable = True

    # Print whether repository is loadable
    print('\\nIs repository loadable -->',loadable)


    # remove all repo data
    REP.remove_repository(removeEmptyDirs=True)

    # check if there is a repository in path
    print( "\\n\\nIs path '%s' a repository --> %s"%(PATH, str(REP.is_repository(PATH))) )


output
======

.. code-block:: python

    repository path --> None

    Is path '/Users/BA642A/pyrepTest_canBeDeleted' a repository --> False
    Repository path --> /Users/BA642A/pyrepTest_canBeDeleted

    Pulled text data --> [ 0.5496571   0.8600462   0.05659633]

    Pulled pickled data --> [ 0.54965711  0.86004617  0.05659633]

    Update pickled data to --> This is an updated string

    walk repository files relative path
    ------------------------------------
    pickled
    text.dat
    folder1/folder2/folder3/folder3Pickled.pkl
    folder1/archive1/archive1Pickled1
    folder1/archive1/archive1Pickled2
    folder1/archive1/archive2/archive2Pickled1

    walk repository directories relative path
    ------------------------------------------
    folder1
    directory1
    folder1/folder2
    folder1/archive1
    folder1/folder2/folder3
    folder1/archive1/archive2
    folder1/archive1/archive2/archive3
    folder1/archive1/archive2/archive3/archive3
    directory1/directory2

    Repository print -->
    /Users/BA642A/pyrepTest_canBeDeleted
      pickled
      text.dat
      /directory1
        /directory2
      /folder1
        /archive1
        archive1Pickled1
        archive1Pickled2
          /archive2
          archive2Pickled1
            /archive3
              /archive3
        /folder2
          /folder3
          folder3Pickled.pkl

    Repository representation -->
    pyrep Repository (Version 3.0.0) @/Users/BA642A/pyrepTest_canBeDeleted [6 files] [9 directories]

    Repository to list -->
    : {'pyrepdirinfo': True, 'type': 'dir', 'exists': True}
    pickled: {'pyrepfileinfo': True, 'type': 'file', 'exists': True}
    text.dat: {'pyrepfileinfo': True, 'type': 'file', 'exists': True}
    directory1: {'pyrepdirinfo': True, 'type': 'dir', 'exists': True}
    directory1/directory2: {'pyrepdirinfo': True, 'type': 'dir', 'exists': True}
    folder1: {'pyrepdirinfo': True, 'type': 'dir', 'exists': True}
    folder1/archive1: {'pyrepdirinfo': True, 'type': 'dir', 'exists': True}
    folder1/archive1/archive1Pickled1: {'pyrepfileinfo': True, 'type': 'file', 'exists': True}
    folder1/archive1/archive1Pickled2: {'pyrepfileinfo': True, 'type': 'file', 'exists': True}
    folder1/archive1/archive2: {'pyrepdirinfo': True, 'type': 'dir', 'exists': True}
    folder1/archive1/archive2/archive2Pickled1: {'pyrepfileinfo': True, 'type': 'file', 'exists': True}
    folder1/archive1/archive2/archive3: {'pyrepdirinfo': True, 'type': 'dir', 'exists': True}
    folder1/archive1/archive2/archive3/archive3: {'pyrepdirinfo': True, 'type': 'dir', 'exists': True}
    folder1/folder2: {'pyrepdirinfo': True, 'type': 'dir', 'exists': True}
    folder1/folder2/folder3: {'pyrepdirinfo': True, 'type': 'dir', 'exists': True}
    folder1/folder2/folder3/folder3Pickled.pkl: {'pyrepfileinfo': True, 'type': 'file', 'exists': True}

    Create package from repository ...

    Is repository loadable --> True

    Is path '/Users/BA642A/pyrepTest_canBeDeleted' a repository --> False
"""

# standard distribution imports
from __future__ import print_function
import os, sys, time, uuid, warnings, tarfile, shutil, traceback, inspect
from datetime import datetime
from functools import wraps
from pprint import pprint
from distutils.dir_util import copy_tree
import copy
try:
    import cPickle as pickle
except:
    import pickle

# import pylocker ServerLocker singleton implementation
from pylocker import ServerLocker, FACTORY

# pyrep imports
from .__pkginfo__ import __version__

# python version dependant imports
if sys.version_info >= (3, 0):
    # This is python 3
    str        = str
    long       = int
    unicode    = str
    bytes      = bytes
    basestring = str
    def makedirs(name, mode=0o777):
        return os.makedirs(name=name, mode=mode, exist_ok=True)
else:
    str        = str
    unicode    = unicode
    bytes      = str
    long       = long
    basestring = basestring
    def makedirs(name, mode=0o777):
        return os.makedirs(name=name, mode=mode)

# set warnings filter to always
warnings.simplefilter('always')


def get_pickling_errors(obj, seen=None):
    """Investigate pickling errors."""
    if seen == None:
        seen = []
    if hasattr(obj, "__getstate__"):
        state = obj.__getstate__()
    else:
        return None
    if state == None:
        return 'object state is None'
    if isinstance(state,tuple):
        if not isinstance(state[0], dict):
            state=state[1]
        else:
            state=state[0].update(state[1])
    result = {}
    for i in state:
        try:
            pickle.dumps(state[i], protocol=2)
        except pickle.PicklingError as e:
            if not state[i] in seen:
                seen.append(state[i])
                result[i]=get_pickling_errors(state[i],seen)
    return result



def get_dump_method(dump, protocol=-1):
    """Get dump function code string"""
    if dump is None:
        dump = 'pickle'
    if dump.startswith('pickle'):
        if dump == 'pickle':
            proto = protocol
        else:
            proto = dump.strip('pickle')
        try:
            proto = int(proto)
            assert proto>=-1
        except:
            raise Exception("protocol must be an integer >=-1")
        code = """
def dump(path, value):
    import os
    try:
        import cPickle as pickle
    except:
        import pickle
    with open(path, 'wb') as fd:
        pickle.dump( value, fd, protocol=%i )
        fd.flush()
        os.fsync(fd.fileno())
"""%proto
    elif dump.startswith('dill'):
        if dump == 'dill':
            proto = 2
        else:
            proto = dump.strip('dill')
            try:
                proto = int(proto)
                assert proto>=-1
            except:
                raise Exception("protocol must be an integer >=-1")
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
    with open(path, 'wb') as fd:
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
        assert isinstance(dump, basestring), "dump must be None or a string"
        code = dump
    # return
    return code




def get_pull_method(pull):
    """Get pull function code string"""
    if pull is None or pull.startswith('pickle'):
        code = """
def pull(path):
    try:
        import cPickle as pickle
    except:
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
        assert isinstance(pull, basestring), "pull must be None or a string"
        code = pull
    # return
    return code



def path_required(func):
    """Decorate methods when repository path is required."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.path is None:
            warnings.warn('Must load (Repository.load_repository) or initialize (Repository.create_repository) the repository first !')
            return
        return func(self, *args, **kwargs)
    return wrapper


class InterpreterError(Exception): pass

def my_exec(cmd, name, description):
    try:
        l = {}
        exec(cmd, l)
        func = l[name]
    except SyntaxError as err:
        error_class = err.__class__.__name__
        detail = err.args[0]
        line_number = err.lineno
    except Exception as err:
        error_class = err.__class__.__name__
        detail = err.args[0]
        cl, exc, tb = sys.exc_info()
        line_number = traceback.extract_tb(tb)[-1][1]
    else:
        return func
    raise InterpreterError("%s at line %d of %s: %s" % (error_class, line_number, description, detail))





def copy_tree(src, dst, srcDirDict,
              filAttr=['.%s_pyrepfileinfo','.%s_pyrepfileclass'],
              dirAttr=['.pyrepdirinfo','.pyreprepo']):
    """copy repository directory tree from source to destination
    Stopped using from distutils.dir_util.copy_tree for 2 reasons.
    #. If in the same session dst is removed, this will fail (it's a bug in distutils)
    #. better to reimplement to copy reporsitory files only using srcDirDict
    """
    files = []
    assert os.path.isdir(src), "given source directory '%s' does not exist"%src
    src = src.rstrip(os.sep)
    dst = dst.rstrip(os.sep)
    assert src!=dst, "source and destination directories are given the same '%s'"%src
    assert isinstance(srcDirDict, dict), "source directory dictionary must be a dictionary "
    assert len(srcDirDict) == 1, "source directory dictionary must be a dictionary of length 1"
    dirName = list(srcDirDict)[0]
    dirList = srcDirDict[dirName]
    srcDirName = os.path.basename(src)
    assert dirName == srcDirName, "source directory dictionary single key must be the source directory name '%s' but '%s' is found"%(srcDirName, dirName)
    # create destination directory
    if not os.path.isdir(dst):
        makedirs(dst)
        for attr in dirAttr:
            srcp = os.path.join(src, attr)
            if os.path.isfile(srcp):
                dstp = os.path.join(dst, attr)
                shutil.copyfile(srcp, dstp)
    # copy files
    for f in dirList:
        if isinstance(f, basestring):
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
            assert len(d) == 1
            fname = list(d)[0]
            src1  = os.path.join(src,fname)
            dst1  = os.path.join(dst,fname)
            files.extend( copy_tree(src=src1, dst=dst1, srcDirDict=d, filAttr=filAttr, dirAttr=dirAttr) )
    # return files
    return files




class Repository(object):
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
        #. pickleProtocol (int): Pickle protocol. Default value is 2 which makes
           it compatible with python 3 and 2. If user is always going to be
           using the same version of python, pickle.HIGHEST_PROTOCOL or -1
           will ensure the highest protocol.
        #. timeout (number): The maximum delay or time allowed to successfully
           set the lock upon reading or writing to the repository
        #. password (None, string): the locker password to manage the
           repository access. If None, default password is given
    """
    DEBUG_PRINT_FAILED_TRIALS = False#True

    def __init__(self, path=None, pickleProtocol=2, timeout=10, password=None):
        self.__repoLock  = '.pyreplock'
        self.__repoFile  = '.pyreprepo'
        self.__dirInfo   = '.pyrepdirinfo'
        self.__dirLock   = '.pyrepdirlock'
        self.__fileInfo  = '.%s_pyrepfileinfo'  # %s replaces file name
        self.__fileClass = '.%s_pyrepfileclass'  # %s replaces file name
        self.__fileLock  = '.%s_pyrepfilelock'  # %s replaces file name
        #self.__objectDir = '.%s_pyrepobjectdir' # %s replaces file name
        if password is None:
            password = "pyrep_repository_b@11a"
        assert isinstance(password, basestring), "password must be None or a string"
        self.__password = password
        self.__locker   = None
        # set default protocols
        assert isinstance(pickleProtocol, int), "pickleProtocol must be integer"
        assert pickleProtocol>=-1, "pickleProtocol must be >=-1"
        self._DEFAULT_PICKLE_PROTOCOL = pickleProtocol
        # initialize repository
        self.reset()
        # if path is not None, load existing repository
        if path is not None:
            assert self.is_repository(path), "given path is not a repository. use create_repository or give a valid repository path"
            self.load_repository(path)
        # set timeout
        self.timeout = timeout

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
        return state

    def __setstate__(self, state):
        path   = state['_Repository__path']
        locker = None
        if path is not None:
            repoLock   = state['_Repository__repoLock']
            password   = state['_Repository__password']
            serverFile = os.path.join(path, repoLock)
            locker = FACTORY(key=serverFile, password=password, serverFile=serverFile, autoconnect=False, reconnect=False)
            locker.start()
        state['_Repository__locker'] = locker
        # set state
        self.__dict__ = state


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
                        if not isinstance(dn, basestring):
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
                    elif isinstance(k, basestring):
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

    #def __setstate__(self, state):
    #    self.__dict__ = state
    #    # start locker if path is not None
    #    if self.__dict__['_Repository__path'] is not None:
    #        #self.__dict__['_Repository__locker'].start()
    #        repoPath   = self.__dict__['_Repository__path']
    #        repolock   = self.__dict__['_Repository__repoLock']
    #        password   = self.__dict__['_Repository__password']
    #        serverFile = os.path.join(repoPath, repolock)
    #        self.__locker = FACTORY(key=serverFile, password=password, serverFile=serverFile, autoconnect=False, reconnect=False)
    #        self.__locker.start()


    @property
    def len(self):
        ndirs, nfiles = self.get_stats()
        return {'number_of_directories':ndirs, 'number_of_files':nfiles}

    @property
    def locker(self):
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
            with open(dirInfoPath, 'wb') as fd:
                pickle.dump( info,fd, protocol=self._DEFAULT_PICKLE_PROTOCOL )
                fd.flush()
                os.fsync(fd.fileno())

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
                    removeFiles.append(os.path.join(self.__path,relaPath))
                    removeFiles.append(os.path.join(self.__path,relaPath,self.__fileInfo%basename))
                    removeFiles.append(os.path.join(self.__path,relaPath,self.__fileLock%basename))
                else:
                    ### MUST VERIFY THAT ONCE pyrepobjectdir IS IMPLEMENTED
                    removeDirs.append(os.path.join(self.__path,relaPath))
                    removeFiles.append(os.path.join(self.__path,relaPath,self.__fileInfo%basename))
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
                                errors.append("Unable to clean directory '%s' (%s)"%(fpath, str(err)))
        # return result and errors list
        return len(errors)==0, errors

    #def __set_repository_directory(self, relativePath, dirList):
    #    splitted = self.to_repo_relative_path(path=relativePath, split=True)
    #    if splitted == ['']:
    #        self.__repo['walk_repo'] = dirList
    #        return True, ""
    #    error = None
    #    cDir  = self.__repo['walk_repo']
    #    for idx, dirname in enumerate(splitted):
    #        dList = [d for d in cDir if isinstance(d, dict)]
    #        if not len(dList):
    #            cDir = None
    #            error = "Repository relative directory '%s' not found"%os.sep.join(splitted[:idx])
    #            break
    #        cDict = [d for d in dList if dirname in d]
    #        if not len(cDict):
    #            cDir = None
    #            error = "Repository relative directory '%s' not found"%os.sep.join(splitted[:idx])
    #            break
    #        if idx == len(splitted)-1:
    #            cDict[0][dirname] = dirList
    #        else:
    #            cDir = cDict[0][dirname]
    #    # return
    #    return False, error

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
            acquired, lockId = self.__locker.acquire_lock(path=self.__path, timeout=self.timeout)
            # check if acquired.
            if not acquired:
                error = "code %s. Unable to aquire the repository lock. You may try again!"%(lockId,)
                assert not raiseError, Exception(error)
                return False,error
        try:
            repoInfoPath = os.path.join(self.__path, self.__repoFile)
            with open(repoInfoPath, 'wb') as fd:
                self.__repo["last_update_utctime"] = time.time()
                pickle.dump( self.__repo,fd, protocol=self._DEFAULT_PICKLE_PROTOCOL )
                fd.flush()
                os.fsync(fd.fileno())
        except Exception as err:
            error = "Unable to save repository (%s)"%str(err)
        # release lock
        if lockFirst:
            self.__locker.release_lock(lockId)
        # return
        assert error is None or not raiseError, error
        return error is None, error

    def __load_repository_pickle_file(self, repoPath):
        try:
            fd = open(repoPath, 'rb')
        except Exception as err:
            raise Exception("Unable to open repository file(%s)"%str(err))
        # read
        try:
            repo = pickle.load( fd )
        except Exception as err:
            fd.close()
            raise Exception("Unable to load pickle repository (%s)"%str(err) )
        else:
            fd.close()
        # check if it's a pyreprepo instance
        assert isinstance(repo, dict), "pyrep repo must be a dictionary"
        assert "create_utctime" in repo, "'create_utctime' must be a key in pyrep repo dict"
        assert "last_update_utctime" in repo, "'last_update_utctime' must be a key in pyrep repo dict"
        assert "pyrep_version" in repo, "'pyrep_version' must be a key in pyrep repo dict"
        assert "walk_repo" in repo, "'walk_repo' must be a key in pyrep repo dict"
        assert isinstance(repo['walk_repo'], list), "pyrep info 'walk_repo' key value must be a list"
        # return
        return repo

    def __load_repository(self, path, verbose=True, safeMode=True):
        # try to open
        if path.strip() in ('','.'):
            path = os.getcwd()
        repoPath = os.path.realpath( os.path.expanduser(path) )
        if not self.is_repository(repoPath):
            raise Exception("No repository found in '%s'"%str(repoPath))
        # update locker serverFile and start
        serverFile    = os.path.join(repoPath, self.__repoLock)
        self.__locker = FACTORY(key=serverFile, password=self.__password, serverFile=serverFile, autoconnect=False, reconnect=False)
        self.__locker.start()
        # acquire lock
        if safeMode:
            acquired, lockId = self.__locker.acquire_lock(path=repoPath, timeout=self.timeout)
            # check if acquired.
            assert acquired, "code %s. Unable to aquire the lock when calling 'load_repository'"%(lockId,)
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
        assert error is None, error

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

    def close(self):
        if self.__locker is not None:
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
                #raise Exception('Not sure what to do next. Please report issue')
        return ndirs,nfiles


    def reset(self):
        """Reset repository instance.
        """
        self.__path   = None
        self.__locker = None
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


    def load_repository(self, path, verbose=True, ntrials=3, safeMode=True):
        """
        Load repository from a directory path and update the current instance.
        First, new repository still will be loaded. If failed, then old
        style repository load will be tried.

        :Parameters:
            #. path (string): The path of the directory from where to load
               the repository from. If '.' or an empty string is passed,
               the current working directory will be used.
            #. verbose (boolean): Whether to be verbose about abnormalities
            #. ntrials (int): After aquiring all locks, ntrials is the maximum
               number of trials allowed before failing. In rare cases, when
               multiple processes are accessing the same repository components,
               different processes can alter repository components between
               successive lock releases of some other process. Bigger number
               of trials lowers the likelyhood of failure due to multiple
               processes same time alteration.
            #. safeMode (boolean): loading repository can be done without
               acquiring from multiple processes. Not acquiring the lock
               can be unsafe if another process is altering the repository

        :Returns:
             #. repository (pyrep.Repository): returns self repository with loaded data.
        """
        assert isinstance(safeMode, bool), "safeMode must be boolean"
        assert isinstance(ntrials, int), "ntrials must be integer"
        assert ntrials>0, "ntrials must be >0"
        repo = None
        for _trial in range(ntrials):
            try:
                self.__load_repository(path=path, verbose=True, safeMode=safeMode)
            except Exception as err1:
                error = "Unable to load repository (%s)"%(err1, )
            else:
                error = None
                repo  = self
                break
        # check and return
        assert error is None, error
        return repo

    def create_repository(self, path, info=None, description=None, replace=True, allowNoneEmpty=True, raiseError=True):
        """
        create a repository in a directory. This method insures the creation of
        the directory in the system if it is missing.\n

        **N.B. If replace is True and existing repository is found in path, create_repository erases all existing files and directories in path.**

        :Parameters:
            #. path (string): The real absolute path where to create the Repository.
               If '.' or an empty string is passed, the current working directory will be used.
            #. description (None, str): Repository main directory information.
            #. info (None, object): Repository information. It can
               be None or any pickle writable type of data.
            #. replace (boolean): Whether to replace existing repository.
            #. allowNoneEmpty (boolean): Allow creating repository in none-empty
               directory.
            #. raiseError (boolean): Whether to raise encountered error instead
               of returning failure.

        :Returns:
            #. success (boolean): Whether creating repository was successful
            #. message (None, str): Any returned message.
        """
        assert isinstance(raiseError, bool), "raiseError must be boolean"
        assert isinstance(allowNoneEmpty, bool), "allowNoneEmpty must be boolean"
        assert isinstance(replace, bool), "replace must be boolean"
        assert isinstance(path, basestring), "path must be string"
        if info is None:
            info = ''
        try:
            pickle.dumps(info)
        except Exception as err:
            raise Exception("info must be None or any pickle writable type of data (%s)"%str(err))
        #assert isinstance(info, basestring), "info must be None or a string"
        if description is None:
            description = ''
        assert isinstance(description, basestring), "description must be None or a string"
        # get real path
        if path.strip() in ('','.'):
            path = os.getcwd()
        realPath = os.path.realpath( os.path.expanduser(path) )
        # reset if replace is set to True
        message = []
        if self.is_repository(realPath):
            if not replace:
                message.append("A pyrep Repository already exists in the given path '%s' set replace to True if you need to proceed."%path)
                return False, message
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
            makedirs(realPath)
        elif len(os.listdir(realPath)) and not allowNoneEmpty:
            return False, "Not allowed to create repository in a non empty directory"
        # reset repository
        oldRepo = self.__repo
        oldPath = self.__path
        self.reset()
        self.__path = realPath.rstrip(os.sep)
        self.__repo['repository_information'] = info
        # set locker
        serverFile    = os.path.join(self.__path, self.__repoLock)
        self.__locker = FACTORY(key=serverFile, password=self.__password, serverFile=serverFile, autoconnect=False, reconnect=False)
        self.__locker.start()
        # save repository
        saved = self.save(description=description)
        if not saved:
            self.__repo = oldRepo
            self.__path = oldPath
            message.append("Absolute path and directories might be created but no pyrep Repository is created. Previous repository state restored")
            if self.__path is not None:
                serverFile    = os.path.join(self.__path, self.__repoLock)
                self.__locker = FACTORY(key=serverFile, password=self.__password, serverFile=serverFile, autoconnect=False, reconnect=False)
                self.__locker.start()
            return False, '\n'.join(message)
        # return
        return True, '\n'.join(message)

    def remove_repository(self, path=None, password=None, removeEmptyDirs=True):
        """
        Remove all repository from path along with all repository tracked files.

        :Parameters:
            #. path (None, string): The path the repository to remove.
            #. password (None, string): If path is not for this isntance
               repository, a new Repository must be created and this
               password would be given upon instanciation
            #. removeEmptyDirs (boolean): Whether to remove remaining empty
               directories including repository one.
        """
        assert isinstance(removeEmptyDirs, bool), "removeEmptyDirs must be boolean"
        if path is not None:
            if path != self.__path:
                repo = Repository(password=password)
                repo.load_repository(path)
            else:
                repo = self
        else:
            repo = self
        assert repo.path is not None, "path is not given and repository is not initialized"
        assert repo.locker.isServer, "It's not safe to remove repository tree from a client"
        assert not len(repo.locker._clientsLUT), "It's not safe to remove repository tree when other instances are still connected"
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
        if not len(os.listdir(repo.path)) and removeEmptyDirs:
            shutil.rmtree( repo.path )
        # close repo
        repo.close()

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
            #. ntrials (int): After aquiring all locks, ntrials is the maximum
               number of trials allowed before failing.
               In rare cases, when multiple processes
               are accessing the same repository components, different processes
               can alter repository components between successive lock releases
               of some other process. Bigger number of trials lowers the
               likelyhood of failure due to multiple processes same time
               alteration.

        :Returns:
            #. success (bool): Whether saving was successful.
            #. error (None, string): Fail to save repository message in case
               saving is not successful. If success is True, error will be None.
        """
        assert isinstance(raiseError, bool), "raiseError must be boolean"
        assert isinstance(ntrials, int), "ntrials must be integer"
        assert ntrials>0, "ntrials must be >0"
        # get description
        if description is not None:
            assert isinstance(description, basestring), "description must be None or a string"
        dirInfoPath = os.path.join(self.__path, self.__dirInfo)
        if description is None and not os.path.isfile(dirInfoPath):
            description = ''
        # create and acquire lock
        acquired, lockId = self.__locker.acquire_lock(self.__path, timeout=self.timeout)
        # check if acquired.
        if not acquired:
            m = "code %s. Unable to aquire the lock when calling 'save'. You may try again!"%(lockId,)
            assert not raiseError, Exception(m)
            return False, m
        # save repository
        for _trial in range(ntrials):
            try:
                # open file
                repoInfoPath = os.path.join(self.__path, self.__repoFile)
                error = None
                self.__save_dirinfo(description=description, dirInfoPath=dirInfoPath)
                # load and update repository info if existing
                if os.path.isfile(repoInfoPath):
                    with open(repoInfoPath, 'rb') as fd:
                        repo = self.__load_repository_pickle_file(os.path.join(self.__path, self.__repoFile))
                        self.__repo['walk_repo'] = repo['walk_repo']
                # create repository
                with open(repoInfoPath, 'wb') as fd:
                    self.__repo["last_update_utctime"] = time.time()
                    pickle.dump( self.__repo,fd, protocol=self._DEFAULT_PICKLE_PROTOCOL )
                    fd.flush()
                    os.fsync(fd.fileno())
            except Exception as err:
                error = "Unable to save repository (%s)"%err
                if self.DEBUG_PRINT_FAILED_TRIALS: print("Trial %i failed in Repository.%s (%s). Set Repository.DEBUG_PRINT_FAILED_TRIALS to False to mute"%(_trial, inspect.stack()[1][3], str(error)))
            else:
                break
        # release lock
        self.__locker.release_lock(lockId)
        # return
        assert error is None or not raiseError, error
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
        assert isinstance(path, basestring), "given path must be a string"
        name = os.path.basename(path)
        if not len(name):
            return False, "empty name is not allowed"
        # exact match
        for em in [self.__repoLock,self.__repoFile,self.__dirInfo,self.__dirLock]:
            if name == em:
                return False, "name '%s' is reserved for pyrep internal usage"%em
        # pattern match
        for pm in [self.__fileInfo,self.__fileLock]:#,self.__objectDir]:
            if name == pm or (name.endswith(pm[3:]) and name.startswith('.')):
                return False, "name pattern '%s' is not allowed as result may be reserved for pyrep internal usage"%pm
        # name is ok
        return True, None

    def to_repo_relative_path(self, path, split=False):
        """
        Given a path, return relative path to diretory

        :Parameters:
            #. path (str): Path as a string
            #. split (boolean): Whether to split path to its components

        :Returns:
            #. relativePath (str, list): Relative path as a string or as a list
               of components if split is True
        """
        path = os.path.normpath(path)
        if path == '.':
            path = ''
        path = path.split(self.__path)[-1].strip(os.sep)
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

                   * 'type': the type of the tracked whether it's file, dir, or objectdir
                   * 'exists': whether file or directory actually exists on disk
                   * 'pyrepfileinfo': In case of a file or an objectdir whether .%s_pyrepfileinfo exists
                   * 'pyrepdirinfo': In case of a directory whether .pyrepdirinfo exists
        """
        state = []
        def _walk_dir(relaPath, dirList):
            dirDict = {'type':'dir',
                       'exists':os.path.isdir(os.path.join(self.__path,relaPath)),
                       'pyrepdirinfo':os.path.isfile(os.path.join(self.__path,relaPath,self.__dirInfo)),
                      }
            state.append({relaPath:dirDict})
            # loop files and dirobjects
            for fname in sorted([f for f in dirList if isinstance(f, basestring)]):
                relaFilePath = os.path.join(relaPath,fname)
                realFilePath = os.path.join(self.__path,relaFilePath)
                #if os.path.isdir(realFilePath) and df.startswith('.') and df.endswith(self.__objectDir[3:]):
                #    fileDict = {'type':'objectdir',
                #                'exists':True,
                #                'pyrepfileinfo':os.path.isfile(os.path.join(self.__path,relaPath,self.__fileInfo%fname)),
                #               }
                #else:
                #    fileDict = {'type':'file',
                #                'exists':os.path.isfile(realFilePath),
                #                'pyrepfileinfo':os.path.isfile(os.path.join(self.__path,relaPath,self.__fileInfo%fname)),
                #               }
                fileDict = {'type':'file',
                            'exists':os.path.isfile(realFilePath),
                            'pyrepfileinfo':os.path.isfile(os.path.join(self.__path,relaPath,self.__fileInfo%fname)),
                           }
                state.append({relaFilePath:fileDict})
            # loop directories
            #for ddict in sorted([d for d in dirList if isinstance(d, dict) and len(d)], key=lambda k: list(k)[0]):
            for ddict in sorted([d for d in dirList if isinstance(d, dict)], key=lambda k: list(k)[0]):
                dirname = list(ddict)[0]
                _walk_dir(relaPath=os.path.join(relaPath,dirname), dirList=ddict[dirname])
        # call recursive _walk_dir
        if relaPath is None:
            _walk_dir(relaPath='', dirList=self.__repo['walk_repo'])
        else:
            assert isinstance(relaPath, basestring), "relaPath must be None or a str"
            relaPath = self.to_repo_relative_path(path=relaPath, split=False)
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
        return copy.deepcopy(self.__get_repository_directory(relativePath))

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
        isRepoFile,fileOnDisk, infoOnDisk, classOnDisk = self.is_repository_file(relativePath)
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
        #if name not in cDir:
        if str(name) not in [str(i) for i in cDir]:
            return False, fileOnDisk, infoOnDisk, classOnDisk
        # this is a repository registered file. check whether all is on disk
        return True, fileOnDisk, infoOnDisk, classOnDisk

    @path_required
    def walk_files_path(self, relativePath="", fullPath=False, recursive=False):
        """
        Walk the repository relative path and yield file relative/full path.

        :parameters:
            #. relativePath (string): The relative path from which start the walk.
            #. fullPath (boolean): Whether to return full or relative path.
            #. recursive (boolean): Whether walk all directories files recursively
        """
        assert isinstance(fullPath, bool), "fullPath must be boolean"
        assert isinstance(recursive, bool), "recursive must be boolean"
        relativePath = self.to_repo_relative_path(path=relativePath, split=False)
        dirList      = self.__get_repository_directory(relativePath=relativePath)
        assert dirList is not None, "given relative path '%s' is not a repository directory"%relativePath
        # walk recursive function
        def _walk(rpath, dlist,recursive):
            # walk files
            for fname in dlist:
                if isinstance(fname, basestring):
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

        :parameters:
            #. relativePath (string): The relative path from which start the walk.
            #. fullPath (boolean): Whether to return full or relative path.
            #. recursive (boolean): Whether walk all directories files recursively
        """
        assert isinstance(fullPath, bool), "fullPath must be boolean"
        assert isinstance(recursive, bool), "recursive must be boolean"
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

        :parameters:
            #. relativePath (string): The relative path from which start the walk.
            #. fullPath (boolean): Whether to return full or relative path.
            #. recursive (boolean): Whether walk all directories files recursively.
        """
        assert isinstance(fullPath, bool), "fullPath must be boolean"
        assert isinstance(recursive, bool), "recursive must be boolean"
        relativePath = self.to_repo_relative_path(path=relativePath, split=False)
        dirList      = self.__get_repository_directory(relativePath=relativePath)
        assert dirList is not None, "given relative path '%s' is not a repository directory"%relativePath
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

        :parameters:
            #. relativePath (string): The relative path from which start the walk.
            #. fullPath (boolean): Whether to return full or relative path.
            #. recursive (boolean): Whether walk all directories files recursively.
        """
        assert isinstance(fullPath, bool), "fullPath must be boolean"
        assert isinstance(recursive, bool), "recursive must be boolean"
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
        assert mode in (None, 'w', 'w:', 'w:gz', 'w:bz2'), 'unkown archive mode %s'%str(mode)
        if mode is None:
            #mode = 'w:bz2'
            mode = 'w:'
        # get root
        if path is None:
            root = os.path.split(self.__path)[0]
        elif path.strip() in ('','.'):
            root = os.getcwd()
        else:
            root = os.path.realpath( os.path.expanduser(path) )
        assert os.path.isdir(root), 'absolute path %s is not a valid directory'%path
        # get name
        if name is None:
            ext = mode.split(":")
            if len(ext) == 2:
                if len(ext[1]):
                    ext = "."+ext[1]
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
        # walk directory and create empty directories
        for dpath in sorted(list(self.walk_directories_path(recursive=True))):
            t = tarfile.TarInfo( dpath )
            t.type = tarfile.DIRTYPE
            tarHandler.addfile(t)
            tarHandler.add(os.path.join(self.__path,dpath,self.__dirInfo), arcname=self.__dirInfo)
        # walk files and add to tar
        for fpath in self.walk_files_path(recursive=True):
            relaPath, fname = os.path.split(fpath)
            tarHandler.add(os.path.join(self.__path,fpath), arcname=fname)
            tarHandler.add(os.path.join(self.__path,relaPath,self.__fileInfo%fname), arcname=self.__fileInfo%fname)
            tarHandler.add(os.path.join(self.__path,relaPath,self.__fileClass%fname), arcname=self.__fileClass%fname)
        # save repository .pyrepinfo
        tarHandler.add(os.path.join(self.__path,self.__repoFile), arcname=".pyrepinfo")
        # close tar file
        tarHandler.close()

    #@path_required
    #def maintain_directory(self, relativePath, keep=None, clean=True):
    #    """
    #    Maintain repository directory by keeping files and directories tracked
    #    and removing non tracked files and directories from system.
#
    #    :Parameters:
    #        #. relativePath (string): The relative to the repository path.
    #        #. keep (None, list, tuple, str): the list of tracked files
    #           (str) and directories (tuple) to keep in pyrep repository.
    #           If keep is None, then all files and directories in replaced
    #           directory will be transfered to newly created and tracked
    #           directory.
    #        #. clean (boolean): Whether to os remove any not tracked file or
    #           directory from given relative path.
#
    #    :Returns:
    #        #. success (boolean): Whether maintenance was successful.
    #        #. reason (None, string): Reason why maintenance was not successful.
    #    """
    #    assert isinstance(clean, bool), "clean must be boolean"
    #    assert isinstance(relativePath, str), "relativePath must be a string"
    #    assert clean or keep is not None, "keep must be not None or clean must be True"
    #    if keep is not None:
    #        if isinstance(keep, (str, tuple)):
    #            keep = [keep]
    #        assert isinstance(keep, (list)), "keep must be None a string or a list"
    #        assert all([isinstance(i,(str, tuple)) for i in keep]), "keep list items must be string or tuples"
    #        assert all([len(t)==1 for t in keep if isinstance(t,tuple)]), "keep list tuple items must be of length 1"
    #        assert all([isinstance(t[0], str) for t in keep if isinstance(t,tuple)]), "keep list tuple items unique value must be a string"
    #        keep = set(keep)
    #    # normalise path
    #    relativePath = self.to_repo_relative_path(path=relativePath, split=False)
    #    realPath     = os.path.join(self.__path,relativePath)
    #    error        = None
    #    mustSave     = False
    #    # keep
    #    LD =  Locker(filePath=None, lockPass=str(uuid.uuid1()), lockPath=os.path.join(realPath, self.__dirLock), timeout=self.timeout)
    #    acquired, code = LD.acquire_lock()
    #    if not acquired:
    #        error = "Code %s. Unable to aquire the lock when adding '%s'. All prior directories were added. You may try again, to finish adding directory"%(code,realPath)
    #        return False, error
    #    try:
    #        posList = self.get_repository_directory(relativePath=relativePath)
    #        assert posList is not None, "Unkown relative directory %s"%relativePath
    #        if keep is not None:
    #            _files     = [f for f in posList if isinstance(f, str)]
    #            _dirs      = [f for f in posList if isinstance(f, dict)]
    #            _keepFiles = [k for k in keep if isinstance(k,str)]
    #            _keepDirs  = [k[0] for k in keep if isinstance(k,tuple)]
    #            _keeping   = [f for f in _files if f in _keepFiles]
    #            _keeping.extend( [f for f in _dirs if list(f)[0] in _keepDirs] )
    #            if len(_keeping)!=len(posList):
    #                #self.__set_repository_directory(relativePath, posList)
    #                _ = [posList.pop(0) for _ in range(len(posList))]
    #                posList.extend(_keeping)
    #                mustSave = True
    #    except Exception as err:
    #        error = "Unable to maintan keeping files and directories (%s)"%(str(err),)
    #    finally:
    #        LD.release_lock()
    #    # clean
    #    if clean and error is None:
    #        _keepFiles = [f for f in posList if isinstance(f, str)]
    #        _flocks    = [self.__fileLock%f for f in _keepFiles]
    #        _finfos    = [self.__fileInfo%f for f in _keepFiles]
    #        _keepFiles.extend(_flocks)
    #        _keepFiles.extend(_finfos)
    #        _keepFiles.extend([self.__repoLock,self.__repoFile,self.__dirInfo,self.__dirLock])
    #        _keepDirs  = [list(f)[0] for f in posList if isinstance(f, dict)]
    #        _keepDirs.extend([self.__objectDir%d for d in _keepDirs])
    #        for df in os.listdir(realPath):
    #            dfpath = os.path.join(realPath, df)
    #            if os.path.isdir(dfpath):
    #                if df not in _keepDirs:
    #                    try:
    #                        shutil.rmtree( dfpath )
    #                    except Exception as err:
    #                        error = "Unable to clean repository directory '%s' along with all it's contents (%s)"%(df,str(err))
    #                        break
    #            elif df not in _keepFiles:
    #                try:
    #                    os.remove(dfpath)
    #                except Exception as err:
    #                    error = "Unable to clean repository file '%s' (%s)"%(df,str(err))
    #                    break
    #    elif clean and error is not None:
    #        error += " --> Unable to clean files from disk"
    #    if mustSave:
    #        if error is not None:
    #            error += " --> Unable to save repository from disk"
    #        else:
    #            _, error = self.save()
    #    # return
    #    return error is None, error


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
            #. ntrials (int): After aquiring all locks, ntrials is the maximum
               number of trials allowed before failing.
               In rare cases, when multiple processes
               are accessing the same repository components, different processes
               can alter repository components between successive lock releases
               of some other process. Bigger number of trials lowers the
               likelyhood of failure due to multiple processes same time
               alteration.

        :Returns:
            #. success (boolean): Whether adding the directory was successful.
            #. message (None, string): Reason why directory was not added or
               random information.
        """
        assert isinstance(raiseError, bool), "raiseError must be boolean"
        assert isinstance(relativePath, basestring), "relativePath must be a string"
        if description is not None:
            assert isinstance(description, basestring), "description must be None or a string"
        assert isinstance(ntrials, int), "ntrials must be integer"
        assert ntrials>0, "ntrials must be >0"
        # normalise path
        path = self.to_repo_relative_path(path=relativePath, split=False)
        # whether to replace
        if self.is_repository_directory(path):
            return True, "Directory is already tracked in repository"
        # check whether name is allowed
        allowed, reason = self.is_name_allowed(path)
        if not allowed:
            if raiseError:
                raise Exception(reason)
            return False, reason
        # lock repository
        acquired, repoLockId = self.__locker.acquire_lock(path=self.__path, timeout=self.timeout)
        if not acquired:
            m = "code %s. Unable to aquire the lock to add directory. You may try again!"%(repoLockId,)
            if raiseError:
                raise Exception(m)
            return False,m
        # load repository info
        for _trial in range(ntrials):
            try:
                repo = self.__load_repository_pickle_file(os.path.join(self.__path, self.__repoFile))
                self.__repo['walk_repo'] = repo['walk_repo']
            except Exception as err:
                error = str(err)
                if self.DEBUG_PRINT_FAILED_TRIALS: print("Trial %i failed in Repository.%s (%s). Set Repository.DEBUG_PRINT_FAILED_TRIALS to False to mute"%(_trial, inspect.stack()[1][3], str(error)))
            else:
                error = None
                break
        if error is not None:
            self.__locker.release_lock(repoLockId)
            assert not raiseError, Exception(error)
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
                acquired, dirLockId = self.__locker.acquire_lock(path=dirPath, timeout=self.timeout)
                if not acquired:
                    error = "Code %s. Unable to aquire the lock when adding '%s'. All prior relative directories were added. You may try again, to finish adding directory"%(dirLockId,dirPath)
                    break
            # add to directory
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
                        assert len(dList) == 1, "Same directory name dict is found twice. This should'n have happened. Report issue"
                        posList = dList[0][name]
                except Exception as err:
                    error = "Unable to create directory '%s' info file (%s)"%(dirPath, str(err))
                    if self.DEBUG_PRINT_FAILED_TRIALS: print("Trial %i failed in Repository.%s (%s). Set Repository.DEBUG_PRINT_FAILED_TRIALS to False to mute"%(_trial, inspect.stack()[1][3], str(error)))
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
        assert error is None or not raiseError, error
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
        return copy.deepcopy(self.__get_repository_parent_directory(relativePath))

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
            #. ntrials (int): After aquiring all locks, ntrials is the maximum
               number of trials allowed before failing.
               In rare cases, when multiple processes
               are accessing the same repository components, different processes
               can alter repository components between successive lock releases
               of some other process. Bigger number of trials lowers the
               likelyhood of failure due to multiple processes same time
               alteration.

        :Returns:
            #. success (boolean): Whether removing the directory was successful.
            #. reason (None, string): Reason why directory was not removed.
        """
        assert isinstance(raiseError, bool), "raiseError must be boolean"
        assert isinstance(clean, bool), "clean must be boolean"
        assert isinstance(ntrials, int), "ntrials must be integer"
        assert ntrials>0, "ntrials must be >0"
        # normalise path
        relativePath = self.to_repo_relative_path(path=relativePath, split=False)
        parentPath, dirName = os.path.split(relativePath)
        # check if this is main repository directory
        if relativePath == '':
            return False, "Removing main repository directory is not allowed"
        # check if this is a repository directory
        if not self.is_repository_directory(relativePath):
            return False, "Given relative path '%s' is not a repository path"%relativePath
        # check if directory actually exists on disk
        realPath = os.path.join(self.__path,relativePath)
        if not os.path.isdir(realPath):
            error = "Repository relative directory '%s' seems to be missing. call maintain_repository to fix all issues"
            assert not raiseError, error
            return False, error
        # get and acquire lock
        acquired, dirLockId = self.__locker.acquire_lock(path=os.path.join(self.__path,parentPath), timeout=self.timeout)
        if not acquired:
            error = "Code %s. Unable to aquire the lock when removing '%s'. All prior relative directories were added. You may try again, to finish removing directory"%(dirLockId,realPath)
            assert not raiseError, error
            return False, error
        # lock repository
        acquired, repoLockId = self.__locker.acquire_lock(path=self.__path, timeout=self.timeout)
        if not acquired:
            m = "code %s. Unable to aquire the repository lock. You may try again!"%(repoLockId,)
            assert raiseError,  Exception(m)
            return False,m
        # remove directory
        for _trial in range(ntrials):
            error = None
            try:
                dirList = self.__get_repository_parent_directory(relativePath=relativePath)
                assert dirList is not None, "Given relative path '%s' is not a repository directory"%(relativePath,)
                stateBefore = self.get_repository_state(relaPath=parentPath)
                _files = [f for f in dirList if isinstance(f, basestring)]
                _dirs  = [d for d in dirList if isinstance(d, dict)]
                _dirs  = [d for d in dirList if dirName not in d]
                _ = [dirList.pop(0) for _ in range(len(dirList))]
                dirList.extend(_files)
                dirList.extend(_dirs)
                if clean:
                    shutil.rmtree(realPath)
                else:
                    stateAfter = self.get_repository_state(relaPath=parentPath)
                    success, errors = self.__clean_before_after(stateBefore=stateBefore, stateAfter=stateAfter, keepNoneEmptyDirectory=True)
                    assert success, "\n".join(errors)
            except Exception as err:
                error = str(err)
                if self.DEBUG_PRINT_FAILED_TRIALS: print("Trial %i failed in Repository.%s (%s). Set Repository.DEBUG_PRINT_FAILED_TRIALS to False to mute"%(_trial, inspect.stack()[1][3], str(error)))
            else:
                break
        # return
        if error is None:
            _, error = self.__save_repository_pickle_file(lockFirst=False, raiseError=False)
        # release locks
        self.__locker.release_lock(dirLockId)
        self.__locker.release_lock(repoLockId)
        # check and return
        assert error is None or not raiseError, "Unable to remove directory after %i trials '%s' (%s)"%(relativePath, ntrials, error,)
        return error is None, error


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
            #. ntrials (int): After aquiring all locks, ntrials is the maximum
               number of trials allowed before failing.
               In rare cases, when multiple processes
               are accessing the same repository components, different processes
               can alter repository components between successive lock releases
               of some other process. Bigger number of trials lowers the
               likelyhood of failure due to multiple processes same time
               alteration.

        :Returns:
            #. success (boolean): Whether renaming the directory was successful.
            #. message (None, string): Some explanatory message or error reason
               why directory was not renamed.
        """
        assert isinstance(raiseError, bool), "raiseError must be boolean"
        assert isinstance(ntrials, int), "ntrials must be integer"
        assert ntrials>0, "ntrials must be >0"
        relativePath = self.to_repo_relative_path(path=relativePath, split=False)
        parentPath, dirName = os.path.split(relativePath)
        if relativePath == '':
            error = "Renaming main repository directory is not allowed"
            assert not raiseError, error
            return False, error
        realPath = os.path.join(self.__path,relativePath)
        newRealPath = os.path.join(os.path.dirname(realPath), newName)
        if os.path.isdir(newRealPath):
            error = "New directory path '%s' already exist"%(newRealPath,)
            assert not raiseError, error
            return False, error
        # get directory parent list
        acquired, dirLockId = self.__locker.acquire_lock(os.path.join(self.__path,parentPath), timeout=self.timeout)
        if not acquired:
            error = "Code %s. Unable to aquire repository lock when renaming '%s'. All prior directories were added. You may try again, to finish adding the directory"%(dirLockId,dirPath)
            assert not raiseError, error
            return False, error
        error = None
        # lock repository
        acquired, repoLockId = self.__locker.acquire_lock(path=self.__path, timeout=self.timeout)
        if not acquired:
            m = "Code %s. Unable to aquire directory lock when renaming '%s'. All prior directories were added. You may try again, to finish adding the directory"%(repoLockId,dirPath)
            assert raiseError,  Exception(m)
            return False,m
        # load repository info
        for _trial in range(ntrials):
            try:
                repo = self.__load_repository_pickle_file(os.path.join(self.__path, self.__repoFile))
                self.__repo['walk_repo'] = repo['walk_repo']
            except Exception as err:
                error = str(err)
                if self.DEBUG_PRINT_FAILED_TRIALS: print("Trial %i failed in Repository.%s (%s). Set Repository.DEBUG_PRINT_FAILED_TRIALS to False to mute"%(_trial, inspect.stack()[1][3], str(error)))
            else:
                error = None
                break
        if error is not None:
            self.__locker.release_lock(dirLockId)
            self.__locker.release_lock(repoLockId)
            assert not raiseError, Exception(error)
            return False, error
        # rename directory
        for _trial in range(ntrials):
            error = None
            try:
                dirList = self.__get_repository_parent_directory(relativePath=relativePath)
                assert dirList is not None, "Given relative path '%s' is not a repository directory"%(relativePath,)
                # change dirName in dirList
                _dirDict = [nd for nd in dirList  if isinstance(nd,dict)]
                _dirDict = [nd for nd in _dirDict if dirName in nd]
                assert len(_dirDict) == 1, "This should not have happened. Directory not found in repository. Please report issue"
                # rename directory
                os.rename(realPath, newRealPath)
                # update dirList
                _dirDict[0][newName] = _dirDict[0][dirName]
                _dirDict[0].pop(dirName)
                # update and dump dirinfo
                self.__save_dirinfo(description=None, dirInfoPath=parentPath, create=False)
            except Exception as err:
                error = str(err)
                if self.DEBUG_PRINT_FAILED_TRIALS: print("Trial %i failed in Repository.%s (%s). Set Repository.DEBUG_PRINT_FAILED_TRIALS to False to mute"%(_trial, inspect.stack()[1][3], str(error)))
            else:
                error = None
                break
        if error is None:
            _, error = self.__save_repository_pickle_file(lockFirst=False, raiseError=False)
        # release locks
        self.__locker.release_lock(dirLockId)
        self.__locker.release_lock(repoLockId)
        # check and return
        assert error is None or not raiseError, "Unable to rename directory '%s' to '%s' after %i trials (%s)"%(relativePath, newName, ntrials, error,)
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
            #. ntrials (int): After aquiring all locks, ntrials is the maximum
               number of trials allowed before failing.
               In rare cases, when multiple processes
               are accessing the same repository components, different processes
               can alter repository components between successive lock releases
               of some other process. Bigger number of trials lowers the
               likelyhood of failure due to multiple processes same time
               alteration.

        :Returns:
            #. success (boolean): Whether renaming the directory was successful.
            #. message (None, string): Some explanatory message or error reason
               why directory was not renamed.
        """
        assert isinstance(raiseError, bool), "raiseError must be boolean"
        assert isinstance(overwrite, bool), "overwrite must be boolean"
        assert isinstance(ntrials, int), "ntrials must be integer"
        assert ntrials>0, "ntrials must be >0"
        relativePath = self.to_repo_relative_path(path=relativePath, split=False)
        if relativePath == '':
            m = "Copying to repository main directory is not possible"
            assert not raiseError, m
            return False, m
        realPath     = os.path.join(self.__path,relativePath)
        parentRealPath, dirName = os.path.split(realPath)
        parentRelativePath = os.path.dirname(relativePath)
        if not self.is_repository_directory(relativePath):
            m = "Directory '%s' is not a tracked repository directory"%(relativePath)
            assert not raiseError, m
            return False, m
        newRelativePath = self.to_repo_relative_path(path=newRelativePath, split=False)
        newRealPath     = os.path.join(self.__path,newRelativePath)
        newParentRealPath, newDirName = os.path.split(newRealPath)
        newParentRelativePath = os.path.dirname(newRelativePath)
        if realPath == newRealPath:
            m = "Copying to the same directory is not possible"
            assert not raiseError, m
            return False, m
        if self.is_repository_directory(newRelativePath):
            m = "Directory '%s' is a tracked repository directory"%(newRelativePath)
            assert not raiseError, m
            return False, m
        if os.path.isdir(newRealPath):
            if overwrite:
                try:
                    shutil.rmtree(newRealPath)
                except Exception as err:
                    assert not raiseError, str(err)
                    return False, str(err)
            else:
                error = "New directory path '%s' already exist on disk. Set overwrite to True"%(newRealPath,)
                assert not raiseError, error
                return False, error
        # add directory
        try:
            success, reason = self.add_directory(newParentRelativePath, raiseError=False, ntrials=ntrials)
        except Exception as err:
            reason  = "Unable to add directory (%s)"%(str(err))
            success = False
        if not success:
            assert not raiseError, reason
            return False, reason
        # lock repository
        acquired, repoLockId = self.__locker.acquire_lock(path=self.__path, timeout=self.timeout)
        if not acquired:
            m = "code %s. Unable to aquire the repository lock. You may try again!"%(repoLockId,)
            assert raiseError,  Exception(m)
            return False,m
        try:
            repo = self.__load_repository_pickle_file(os.path.join(self.__path, self.__repoFile))
            self.__repo['walk_repo'] = repo['walk_repo']
        except Exception as err:
            self.__locker.release_lock(repoLockId)
            assert not raiseError, Exception(str(err))
            return False,m
        # create locks
        acquired, dirLockId = self.__locker.acquire_lock(path=parentRealPath, timeout=self.timeout)
        if not acquired:
            self.__locker.release_lock(repoLockId)
            error = "Code %s. Unable to aquire the lock when adding '%s'. All prior directories were added. You may try again, to finish adding directory"%(dirLockId,dirPath)
            assert not raiseError, error
            return False, error
        newDirLockId = None
        if parentRealPath != newParentRealPath:
            acquired, newDirLockId = self.__locker.acquire_lock(path=newParentRealPath, timeout=self.timeout)
            if not acquired:
                self.__locker.release_lock(dirLockId)
                self.__locker.release_lock(repoLockId)
                error = "Code %s. Unable to aquire the lock when adding '%s'. All prior directories were added. You may try again, to finish adding directory"%(newDirLockId,dirPath)
                assert not raiseError, error
                return False, error
        # get directory parent list
        error = None
        for _trial in range(ntrials):
            try:
                # make sure again because sometimes, when multiple processes are working on the same repo things can happen in between
                assert self.is_repository_directory(relativePath), "Directory '%s' is not anymore a tracked repository directory"%(relativePath)
                assert not self.is_repository_directory(newRelativePath), "Directory '%s' has become a tracked repository directory"%(relativePath)
                dirList = self.__get_repository_parent_directory(relativePath=relativePath)
                assert dirList is not None, "Given relative path '%s' is not a repository directory"%(relativePath,)
                newDirList = self.__get_repository_parent_directory(relativePath=newRelativePath)
                assert newDirList is not None, "Given new relative path '%s' parent directory is not a repository directory"%(newRelativePath,)
                # change dirName in dirList
                _dirDict = [nd for nd in dirList  if isinstance(nd,dict)]
                _dirDict = [nd for nd in _dirDict if dirName in nd]
                assert len(_dirDict) == 1, "This should not have happened. Directory not found in repository. Please report issue"
                _dirDict = _dirDict[0]
                _newDirDict = [nd for nd in newDirList  if isinstance(nd,dict)]
                _newDirDict = [nd for nd in _newDirDict if newDirName in nd]
                assert len(_newDirDict) == 0, "This should not have happened. New directory is found in repository. Please report issue"
                # try to copy directory
                _newDirDict = copy.deepcopy(_dirDict)
                if dirName != newDirName:
                    _newDirDict[newDirName] = _newDirDict.pop(dirName)
                _ = copy_tree(src=realPath, dst=newRealPath, srcDirDict=_dirDict,
                              filAttr = [self.__fileInfo,self.__fileClass],
                              dirAttr = [self.__dirInfo,self.__repoFile])
                #_ = copy_tree(realPath, newRealPath)
                # update newDirList
                newDirList.append(_newDirDict)
                # update and dump dirinfo
                self.__save_dirinfo(description=None, dirInfoPath=newParentRelativePath, create=False)
            except Exception as err:
                error = str(err)
                if self.DEBUG_PRINT_FAILED_TRIALS: print("Trial %i failed in Repository.%s (%s). Set Repository.DEBUG_PRINT_FAILED_TRIALS to False to mute"%(_trial, inspect.stack()[1][3], str(error)))
            else:
                error = None
                break
        if error is None:
            _, error = self.__save_repository_pickle_file(lockFirst=False, raiseError=False)
        self.__locker.release_lock(dirLockId)
        self.__locker.release_lock(repoLockId)
        if newDirLockId is not None:
            self.__locker.release_lock(newDirLockId)
        # check and return
        assert error is None or not raiseError, "Unable to copy directory '%s' to '%s' after %i trials (%s)"%(relativePath, newRelativePath, ntrials, error,)
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
            #. dump (None, string): The dumping method.
               If None it will be set automatically to pickle and therefore the
               object must be pickleable. If a string is given, it can be a
               keyword ('json','pickle','dill') or a string compileable code to
               dump the data. The string code must include all the necessary
               imports and a '$FILE_PATH' that replaces the absolute file path
               when the dumping will be performed.\n
               e.g. "import numpy as np; np.savetxt(fname='$FILE_PATH', X=value, fmt='%.6e')"
            #. pull (None, string): The pulling method. If None it will be set
               automatically to pickle and therefore the object must be
               pickleable. If a string is given, it can be a keyword
               ('json','pickle','dill') or a string compileable code to pull
               the data. The string code must include all the necessary imports,
               a '$FILE_PATH' that replaces the absolute file path when the
               dumping will be performed and finally a PULLED_DATA variable.\n
               e.g "import numpy as np; PULLED_DATA=np.loadtxt(fname='$FILE_PATH')"
            #. replace (boolean): Whether to replace any existing file.
            #. raiseError (boolean): Whether to raise encountered error instead
               of returning failure.
            #. ntrials (int): After aquiring all locks, ntrials is the maximum
               number of trials allowed before failing.
               In rare cases, when multiple processes
               are accessing the same repository components, different processes
               can alter repository components between successive lock releases
               of some other process. Bigger number of trials lowers the
               likelyhood of failure due to multiple processes same time
               alteration.

        :Returns:
            #. success (boolean): Whether renaming the directory was successful.
            #. message (None, string): Some explanatory message or error reason
               why directory was not dumped.
        """
        # check arguments
        assert isinstance(raiseError, bool), "raiseError must be boolean"
        assert isinstance(replace, bool), "replace must be boolean"
        assert isinstance(ntrials, int), "ntrials must be integer"
        assert ntrials>0, "ntrials must be >0"
        if description is None:
            description = ''
        assert isinstance(description, basestring), "description must be None or a string"
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
            assert not raiseError, reason
            return False, reason
        # ensure directory added
        try:
            success, reason = self.add_directory(fPath, raiseError=False, ntrials=ntrials)
        except Exception as err:
            reason  = "Unable to add directory (%s)"%(str(err))
            success = False
        if not success:
            assert not raiseError, reason
            return False, reason
        # lock repository
        acquired, repoLockId = self.__locker.acquire_lock(path=self.__path, timeout=self.timeout)
        if not acquired:
            m = "code %s. Unable to aquire the repository lock. You may try again!"%(repoLockId,)
            assert raiseError, Exception(m)
            return False,m
        # lock file
        acquired, fileLockId = self.__locker.acquire_lock(path=savePath, timeout=self.timeout)
        if not acquired:
            self.__locker.release_lock(repoLockId)
            error = "Code %s. Unable to aquire the lock when dumping '%s'"%(fileLockId,relativePath)
            assert not raiseError, error
            return False, error
        # load repository info
        for _trial in range(ntrials):
            try:
                repo = self.__load_repository_pickle_file(os.path.join(self.__path, self.__repoFile))
                self.__repo['walk_repo'] = repo['walk_repo']
            except Exception as err:
                error = str(err)
                if self.DEBUG_PRINT_FAILED_TRIALS: print("Trial %i failed in Repository.%s (%s). Set Repository.DEBUG_PRINT_FAILED_TRIALS to False to mute"%(_trial, inspect.stack()[1][3], str(error)))
            else:
                error = None
                break
        if error is not None:
            self.__locker.release_lock(dirLockId)
            self.__locker.release_lock(fileLockId)
            assert not raiseError, Exception(error)
            return False, error
        # dump file
        for _trial in range(ntrials):
            error = None
            try:
                isRepoFile, fileOnDisk, infoOnDisk, classOnDisk = self.is_repository_file(relativePath)
                if isRepoFile:
                    assert replace, "file is a registered repository file. set replace to True to replace"
                fileInfoPath = os.path.join(self.__path,os.path.dirname(relativePath),self.__fileInfo%fName)
                if isRepoFile and fileOnDisk:
                    with open(fileInfoPath, 'rb') as fd:
                        info = pickle.load(fd)
                    assert info['repository_unique_name'] == self.__repo['repository_unique_name'], "it seems that file was created by another repository"
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
                dumpFunc(path=str(savePath), value=value)
                # update info
                with open(fileInfoPath, 'wb') as fd:
                    pickle.dump( info,fd, protocol=self._DEFAULT_PICKLE_PROTOCOL)
                    fd.flush()
                    os.fsync(fd.fileno())
                # update class file
                fileClassPath = os.path.join(self.__path,os.path.dirname(relativePath),self.__fileClass%fName)
                with open(fileClassPath, 'wb') as fd:
                    if value is None:
                        klass = None
                    else:
                        klass = value.__class__
                    pickle.dump(klass , fd, protocol=self._DEFAULT_PICKLE_PROTOCOL )
                    fd.flush()
                    os.fsync(fd.fileno())
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
                except:
                    pass
                if self.DEBUG_PRINT_FAILED_TRIALS: print("Trial %i failed in Repository.%s (%s). Set Repository.DEBUG_PRINT_FAILED_TRIALS to False to mute"%(_trial, inspect.stack()[1][3], str(error)))
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
        assert not raiseError or error is None, "unable to dump file '%s' after %i trials (%s)"%(relativePath, ntrials, error,)
        return success, error

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
            #. ntrials (int): After aquiring all locks, ntrials is the maximum
               number of trials allowed before failing.
               In rare cases, when multiple processes
               are accessing the same repository components, different processes
               can alter repository components between successive lock releases
               of some other process. Bigger number of trials lowers the
               likelyhood of failure due to multiple processes same time
               alteration.

        :Returns:
            #. success (boolean): Whether renaming the file was successful.
            #. message (None, string): Some explanatory message or error reason
               why directory was not updated.
        """
        assert isinstance(raiseError, bool), "raiseError must be boolean"
        assert isinstance(force, bool), "force must be boolean"
        assert isinstance(ntrials, int), "ntrials must be integer"
        assert ntrials>0, "ntrials must be >0"
        # check old name and path
        relativePath = self.to_repo_relative_path(path=relativePath, split=False)
        realPath     = os.path.join(self.__path,relativePath)
        fPath, fName = os.path.split(realPath)
        # check new name and path
        newRelativePath = self.to_repo_relative_path(path=newRelativePath, split=False)
        newRealPath     = os.path.join(self.__path,newRelativePath)
        nfPath, nfName  = os.path.split(newRealPath)
        # lock old file
        acquired, fileLockId = self.__locker.acquire_lock(path=realPath, timeout=self.timeout)
        if not acquired:
            error = "Code %s. Unable to aquire the lock for old file '%s'"%(fileLockId,relativePath)
            assert not raiseError, error
            return False, error
        # add new file diretory
        try:
            success, reason = self.add_directory(nfPath, raiseError=False, ntrials=ntrials)
        except Exception as err:
            reason  = "Unable to add directory (%s)"%(str(err))
            success = False
        if not success:
            self.__locker.release_lock(fileLockId)
            assert not raiseError, reason
            return False, reason
        # create new file lock
        acquired, newFileLockId = self.__locker.acquire_lock(path=newRealPath, timeout=self.timeout)
        if not acquired:
            self.__locker.release_lock(fileLlockId)
            error = "Code %s. Unable to aquire the lock for new file path '%s'"%(newFileLockId,newRelativePath)
            assert not raiseError, error
            return False, error
        # copy file
        for _trial in range(ntrials):
            copied = False
            error  = None
            try:
                # check whether it's a repository file
                isRepoFile,fileOnDisk, infoOnDisk, classOnDisk = self.is_repository_file(relativePath)
                assert isRepoFile,  "file '%s' is not a repository file"%(relativePath,)
                assert fileOnDisk,  "file '%s' is found on disk"%(relativePath,)
                assert infoOnDisk,  "%s is found on disk"%self.__fileInfo%fName
                assert classOnDisk, "%s is found on disk"%self.__fileClass%fName
                # get new file path
                nisRepoFile,nfileOnDisk,ninfoOnDisk,nclassOnDisk = self.is_repository_file(newRelativePath)
                assert not nisRepoFile or force, "New file path is a registered repository file, set force to True to proceed regardless"
                # get parent directories list
                nDirList = self.__get_repository_directory(nfPath)
                # remove new file and all repository files from disk
                if os.path.isfile(newRealPath):
                    os.remove(newRealPath)
                if os.path.isfile(os.path.join(nfPath,self.__fileInfo%nfName)):
                    os.remove(os.path.join(nfPath,self.__fileInfo%nfName))
                if os.path.isfile(os.path.join(nfPath,self.__fileClass%nfName)):
                    os.remove(os.path.join(nfPath,self.__fileClass%nfName))
                # move old file to new path
                shutil.copy(realPath, newRealPath)
                shutil.copy(os.path.join(fPath,self.__fileInfo%fName),  os.path.join(nfPath,self.__fileInfo%nfName))
                shutil.copy(os.path.join(fPath,self.__fileClass%fName), os.path.join(nfPath,self.__fileClass%nfName))
                # update new list
                if nfName not in nDirList:
                    nDirList.append(nfName)
            except Exception as err:
                copied = False
                error = str(err)
                if self.DEBUG_PRINT_FAILED_TRIALS: print("Trial %i failed in Repository.%s (%s). Set Repository.DEBUG_PRINT_FAILED_TRIALS to False to mute"%(_trial, inspect.stack()[1][3], str(error)))
            else:
                error = None
                copied = True
                break
        # release locks
        self.__locker.release_lock(fileLockId)
        self.__locker.release_lock(newFileLockId)
        # check and return
        assert copied or not raiseError, "Unable to copy file '%s' to '%s' after %i trials (%s)"%(relativePath, newRelativePath, ntrials, error,)
        return copied, '\n'.join(message)


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
            #. ntrials (int): After aquiring all locks, ntrials is the maximum
               number of trials allowed before failing.
               In rare cases, when multiple processes
               are accessing the same repository components, different processes
               can alter repository components between successive lock releases
               of some other process. Bigger number of trials lowers the
               likelyhood of failure due to multiple processes same time
               alteration.

       :Returns:
           #. success (boolean): Whether renaming the directory was successful.
           #. message (None, string): Some explanatory message or error reason
              why directory was not updated.
        """
        # check arguments
        assert isinstance(raiseError, bool), "raiseError must be boolean"
        assert description is False or description is None or isinstance(description, basestring), "description must be False, None or a string"
        assert dump is False or dump is None or isinstance(dump, basestring), "dump must be False, None or a string"
        assert pull is False or pull is None or isinstance(pull, basestring), "pull must be False, None or a string"
        assert isinstance(ntrials, int), "ntrials must be integer"
        assert ntrials>0, "ntrials must be >0"
        # get name and path
        relativePath = self.to_repo_relative_path(path=relativePath, split=False)
        savePath     = os.path.join(self.__path,relativePath)
        fPath, fName = os.path.split(savePath)
        # get locker
        acquired, fileLockId = self.__locker.acquire_lock(path=savePath, timeout=self.timeout)
        if not acquired:
            error = "Code %s. Unable to aquire the lock to update '%s'"%(fileLockId,relativePath)
            assert not raiseError, error
            return False, error
        # update file
        for _trial in range(ntrials):
            message = []
            updated = False
            try:
                # check file in repository
                isRepoFile, fileOnDisk, infoOnDisk, classOnDisk = self.is_repository_file(relativePath)
                assert isRepoFile, "file '%s' is not registered in repository, no update can be performed."%(relativePath,)
                # get file info
                if not fileOnDisk:
                    assert description is not False,  "file '%s' is found on disk, description must be provided"%(relativePath,)
                    assert dump is not False,  "file '%s' is found on disk, dump must be provided"%(relativePath,)
                    assert pull is not False,  "file '%s' is found on disk, pull must be provided"%(relativePath,)
                    info = {}
                    info['repository_unique_name'] = self.__repo['repository_unique_name']
                    info['create_utctime'] = info['last_update_utctime'] = time.time()
                else:
                    with open(os.path.join(fPath,self.__fileInfo%fName), 'rb') as fd:
                        info = pickle.load(fd)
                        info['last_update_utctime'] = time.time()
                if not fileOnDisk:
                    message.append("file %s is registered in repository but it was found on disk prior to updating"%relativePath)
                if not infoOnDisk:
                    message.append("%s is not found on disk prior to updating"%self.__fileInfo%fName)
                if not classOnDisk:
                    message.append("%s is not found on disk prior to updating"%self.__fileClass%fName)
                # get dump and pull
                if (description is False) or (dump is False) or (pull is False):
                    if description is False:
                        description = info['description']
                    elif description is None:
                        description = ''
                    if dump is False:
                        dump = info['dump']
                    elif dump is None:
                        dump = get_dump_method(dump, protocol=self._DEFAULT_PICKLE_PROTOCOL)
                    if pull is False:
                        pull = info['pull']
                    elif pull is None:
                        pull = get_pull_method(pull)
                # update dump, pull and description
                info['dump'] = dump
                info['pull'] = pull
                info['description'] = description
                # dump file
                dumpFunc = my_exec( dump, name='dump', description='update')
                dumpFunc(path=str(savePath), value=value)
                # remove file if exists
                _path = os.path.join(fPath,self.__fileInfo%fName)
                # update info
                with open(_path, 'wb') as fd:
                    pickle.dump( info,fd, protocol=self._DEFAULT_PICKLE_PROTOCOL )
                    fd.flush()
                    os.fsync(fd.fileno())
                # update class file
                fileClassPath = os.path.join(self.__path,os.path.dirname(relativePath),self.__fileClass%fName)
                with open(fileClassPath, 'wb') as fd:
                    if value is None:
                        klass = None
                    else:
                        klass = value.__class__
                    pickle.dump(klass , fd, protocol=self._DEFAULT_PICKLE_PROTOCOL )
                    fd.flush()
                    os.fsync(fd.fileno())
            except Exception as err:
                message.append(str(err))
                updated = False
                try:
                    if 'pickle.dump(' in dump:
                        mi = get_pickling_errors(value)
                        if mi is not None:
                            message.append('more info: %s'%str(mi))
                except:
                    pass
                if self.DEBUG_PRINT_FAILED_TRIALS: print("Trial %i failed in Repository.%s (%s). Set Repository.DEBUG_PRINT_FAILED_TRIALS to False to mute"%(_trial, inspect.stack()[1][3], '\n'.join(message)))
            else:
                updated = True
                break
        # release lock
        self.__locker.release_lock(fileLockId)
        # check and return
        assert updated or not raiseError, "Unable to update file '%s' (%s)"%(relativePath, '\n'.join(message),)
        return updated, '\n'.join(message)

    def update(self, *args, **kwargs):
        """Alias to update_file"""
        return self.update_file(*args, **kwargs)


    @path_required
    def pull_file(self, relativePath, pull=None, update=True, ntrials=3):
        """
        Pull a file's data from the Repository.

        :Parameters:
            #. relativePath (string): The relative to the repository path from
               where to pull the file.
            #. pull (None, string): The pulling method.
               If None, the pull method saved in the file info will be used.
               If a string is given, the string should include all the necessary
               imports, a '$FILE_PATH' that replaces the absolute file path when
               the dumping will be performed and finally a PULLED_DATA variable.
               e.g "import numpy as np; PULLED_DATA=np.loadtxt(fname='$FILE_PATH')"
            #. update (boolean): If pull is not None, Whether to update the pull
               method stored in the file info by the given pull method.
            #. ntrials (int): After aquiring all locks, ntrials is the maximum
               number of trials allowed before failing.
               In rare cases, when multiple processes
               are accessing the same repository components, different processes
               can alter repository components between successive lock releases
               of some other process. Bigger number of trials lowers the
               likelyhood of failure due to multiple processes same time
               alteration.

        :Returns:
            #. data (object): The pulled data from the file.
        """
        assert isinstance(ntrials, int), "ntrials must be integer"
        assert ntrials>0, "ntrials must be >0"
        # check name and path
        relativePath = self.to_repo_relative_path(path=relativePath, split=False)
        realPath     = os.path.join(self.__path,relativePath)
        fPath, fName = os.path.split(realPath)
        # check whether it's a repository file
        isRepoFile,fileOnDisk, infoOnDisk, classOnDisk = self.is_repository_file(relativePath)
        if not isRepoFile:
            fileOnDisk  = ["",". File itself is found on disk"][fileOnDisk]
            infoOnDisk  = ["",". %s is found on disk"%self.__fileInfo%fName][infoOnDisk]
            classOnDisk = ["",". %s is found on disk"%self.__fileClass%fName][classOnDisk]
            assert False, "File '%s' is not a repository file%s%s%s"%(relativePath,fileOnDisk,infoOnDisk,classOnDisk)
        assert fileOnDisk, "File '%s' is registered in repository but the file itself was not found on disk"%(relativePath,)
        if not infoOnDisk:
            if pull is not None:
                warnings.warn("'%s' was not found on disk but pull method is given"%(self.__fileInfo%fName))
            else:
                raise Exception("File '%s' is registered in repository but the '%s' was not found on disk and pull method is not specified"%(relativePath,(self.__fileInfo%fName)))
        # lock repository
        acquired, fileLockId = self.__locker.acquire_lock(path=realPath, timeout=self.timeout)
        if not acquired:
            error = "Code %s. Unable to aquire the lock when pulling '%s'"%(fileLockId,relativePath)
            return False, error
        # pull file
        for _trial in range(ntrials):
            error = None
            try:
                # get pull method
                if pull is not None:
                    pull = get_pull_method(pull)
                else:
                    with open(os.path.join(fPath,self.__fileInfo%fName), 'rb') as fd:
                        info = pickle.load(fd)
                    pull = info['pull']
                # try to pull file
                pullFunc  = my_exec( pull, name='pull', description='pull')
                pulledVal = pullFunc(path=str(realPath))
            except Exception as err:
                #LF.release_lock()
                self.__locker.release_lock(fileLockId)
                m = str(pull).replace("$FILE_PATH", str(realPath) )
                error = "Unable to pull data using '%s' from file (%s)"%(m,err)
                if self.DEBUG_PRINT_FAILED_TRIALS: print("Trial %i failed in Repository.%s (%s). Set Repository.DEBUG_PRINT_FAILED_TRIALS to False to mute"%(_trial, inspect.stack()[1][3], str(error)))
            else:
                break
        # release lock
        self.__locker.release_lock(fileLockId)
        # check and return
        assert error is None, "After %i trials, %s"%(ntrials, error)
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
            #. ntrials (int): After aquiring all locks, ntrials is the maximum
               number of trials allowed before failing.
               In rare cases, when multiple processes
               are accessing the same repository components, different processes
               can alter repository components between successive lock releases
               of some other process. Bigger number of trials lowers the
               likelyhood of failure due to multiple processes same time
               alteration.

        :Returns:
            #. success (boolean): Whether renaming the file was successful.
            #. message (None, string): Some explanatory message or error reason
               why directory was not updated.
        """
        assert isinstance(raiseError, bool), "raiseError must be boolean"
        assert isinstance(force, bool), "force must be boolean"
        assert isinstance(ntrials, int), "ntrials must be integer"
        assert ntrials>0, "ntrials must be >0"
        # check old name and path
        relativePath = self.to_repo_relative_path(path=relativePath, split=False)
        realPath     = os.path.join(self.__path,relativePath)
        fPath, fName = os.path.split(realPath)
        # check new name and path
        newRelativePath = self.to_repo_relative_path(path=newRelativePath, split=False)
        newRealPath     = os.path.join(self.__path,newRelativePath)
        nfPath, nfName  = os.path.split(newRealPath)
        # lock old file
        acquired, fileLockId = self.__locker.acquire_lock(path=realPath, timeout=self.timeout)
        if not acquired:
            error = "Code %s. Unable to aquire the lock for old file '%s'"%(fileLockId,relativePath)
            assert not raiseError, error
            return False, error
        # add directory
        try:
            success, reason = self.add_directory(nfPath, raiseError=False, ntrials=ntrials)
        except Exception as err:
            reason  = "Unable to add directory (%s)"%(str(err))
            success = False
        if not success:
            #LO.release_lock()
            self.__locker.release_lock(fileLockId)
            assert not raiseError, reason
            return False, reason
        # create new file lock
        acquired, newFileLockId = self.__locker.acquire_lock(path=newRealPath, timeout=self.timeout)
        if not acquired:
            #LO.release_lock()
            self.__locker.release_lock(fileLockId)
            error = "Code %s. Unable to aquire the lock for new file path '%s'"%(newFileLockId,newRelativePath)
            assert not raiseError, error
            return False, error
        # rename file
        for _trial in range(ntrials):
            renamed = False
            error   = None
            try:
                # check whether it's a repository file
                isRepoFile,fileOnDisk, infoOnDisk, classOnDisk = self.is_repository_file(relativePath)
                assert isRepoFile,  "file '%s' is not a repository file"%(relativePath,)
                assert fileOnDisk,  "file '%s' is found on disk"%(relativePath,)
                assert infoOnDisk,  "%s is found on disk"%self.__fileInfo%fName
                assert classOnDisk, "%s is found on disk"%self.__fileClass%fName
                # get new file path
                nisRepoFile,nfileOnDisk,ninfoOnDisk,nclassOnDisk = self.is_repository_file(newRelativePath)
                assert not nisRepoFile or force, "New file path is a registered repository file, set force to True to proceed regardless"
                # get parent directories list
                oDirList = self.__get_repository_directory(fPath)
                nDirList = self.__get_repository_directory(nfPath)
                # remove new file and all repository files from disk
                if os.path.isfile(newRealPath):
                    os.remove(newRealPath)
                if os.path.isfile(os.path.join(nfPath,self.__fileInfo%nfName)):
                    os.remove(os.path.join(nfPath,self.__fileInfo%nfName))
                if os.path.isfile(os.path.join(nfPath,self.__fileClass%nfName)):
                    os.remove(os.path.join(nfPath,self.__fileClass%nfName))
                # move old file to new path
                os.rename(realPath, newRealPath)
                os.rename(os.path.join(fPath,self.__fileInfo%fName), os.path.join(nfPath,self.__fileInfo%nfName))
                os.rename(os.path.join(fPath,self.__fileClass%fName), os.path.join(nfPath,self.__fileClass%nfName))
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
            else:
                renamed = True
                break
        # release locks
        self.__locker.release_lock(fileLockId)
        self.__locker.release_lock(newFileLockId)
        # always clean old file lock
        try:
            if os.path.isfile(os.path.join(fPath,self.__fileLock%fName)):
                os.remove(os.path.join(fPath,self.__fileLock%fName))
        except:
            pass
        # check and return
        assert renamed or not raiseError, "Unable to rename file '%s' to '%s' after %i trials (%s)"%(relativePath, newRelativePath, ntrials, error,)
        return renamed, error


    @path_required
    def remove_file(self, relativePath, removeFromSystem=False,
                          raiseError=True, ntrials=3):
        """
        Remove file from repository.

        :Parameters:
            #. relativePath (string): The relative to the repository path of the
               file to remove.
            #. removeFromSystem (boolean): Whether to remove file from disk as
               well.
            #. raiseError (boolean): Whether to raise encountered error instead
               of returning failure.
            #. ntrials (int): After aquiring all locks, ntrials is the maximum
               number of trials allowed before failing.
               In rare cases, when multiple processes
               are accessing the same repository components, different processes
               can alter repository components between successive lock releases
               of some other process. Bigger number of trials lowers the
               likelyhood of failure due to multiple processes same time
               alteration.
        """
        assert isinstance(raiseError, bool), "removeFromSystem must be boolean"
        assert isinstance(removeFromSystem, bool), "removeFromSystem must be boolean"
        assert isinstance(ntrials, int), "ntrials must be integer"
        assert ntrials>0, "ntrials must be >0"
        # check name and path
        relativePath = self.to_repo_relative_path(path=relativePath, split=False)
        realPath     = os.path.join(self.__path,relativePath)
        fPath, fName = os.path.split(realPath)
        # lock repository
        acquired, fileLockId = self.__locker.acquire_lock(path=realPath, timeout=self.timeout)
        if not acquired:
            error = "Code %s. Unable to aquire the lock when removing '%s'"%(fileLockId,relativePath)
            assert not raiseError, error
            return False, error
        # remove file
        for _trial in range(ntrials):
            removed = False
            message = []
            try:
                # check whether it's a repository file
                isRepoFile,fileOnDisk, infoOnDisk, classOnDisk = self.is_repository_file(relativePath)
                if not isRepoFile:
                    message("File '%s' is not a repository file"%(relativePath,))
                    if fileOnDisk:
                        message.append("File itself is found on disk")
                    if infoOnDisk:
                        message.append("%s is found on disk"%self.__fileInfo%fName)
                    if classOnDisk:
                        message.append("%s is found on disk"%self.__fileClass%fName)
                else:
                    dirList = self.__get_repository_directory(fPath)
                    findex  = dirList.index(fName)
                    dirList.pop(findex)
                    if os.path.isfile(realPath):
                        os.remove(realPath)
                    if os.path.isfile(os.path.join(fPath,self.__fileInfo%fName)):
                        os.remove(os.path.join(fPath,self.__fileInfo%fName))
                    if os.path.isfile(os.path.join(fPath,self.__fileClass%fName)):
                        os.remove(os.path.join(fPath,self.__fileClass%fName))
            except Exception as err:
                removed = False
                message.append(str(err))
                if self.DEBUG_PRINT_FAILED_TRIALS: print("Trial %i failed in Repository.%s (%s). Set Repository.DEBUG_PRINT_FAILED_TRIALS to False to mute"%(_trial, inspect.stack()[1][3], '\n'.join(message)))
            else:
                removed = True
                break
        # release lock
        self.__locker.release_lock(fileLockId)
        # always clean
        try:
            if os.path.isfile(os.path.join(fPath,self.__fileLock%fName)):
                os.remove(os.path.join(fPath,self.__fileLock%fName))
        except:
            pass
        # check and return
        assert removed or not raiseError, "Unable to remove file '%s' after %i trials (%s)"%(relativePath, ntrials, '\n'.join(message),)
        return removed, '\n'.join(message)
