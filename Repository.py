"""
Usage:
======

.. code-block:: python

        # standard distribution imports
        import os
        import warnings
        
        # numpy imports
        import numpy as np
        
        # import Repository
        from pyrep import Repository
        
        # initialize Repository instance
        REP=Repository()
        
        # create a path pointing to user home
        PATH = os.path.join(os.path.expanduser("~"), 'pyrepTest_canBeDeleted')
        
        # check if directory exist
        if os.path.isdir(PATH):
            if not REP.is_repository(PATH):
                warnings.warn("Directory exists and it's not a pyrep repository.")
                exit()
            else:
                # remove repository from directory if repository exist.
                REP.remove_repository(path=PATH, relatedFiles=False, relatedFolders=False)
        
        
        # print repository path
        print "repository path --> %s"%str(REP.path)
        
        # create repository in path
        print "\\nIs path '%s' a repository --> %s"%(PATH, str(REP.is_repository(PATH)))
        REP.create_repository(PATH)
        print '\\nRepository path --> %s'%str(REP.path)
        
        # add directories
        REP.add_directory("folder1/folder2/folder3")
        REP.add_directory("folder1/archive1/archive2/archive3/archive3")
        REP.add_directory("directory1/directory2")
        
        # dump files
        value = "This is a string data to pickle and store in the repository"
        REP.dump_file(value, relativePath='.', name='pickled', dump=None, pull=None, replace=True)
        
        value = np.random.random(3)
        dump="import numpy as np; np.savetxt(fname='$FILE_PATH', X=value, fmt='%.6e')"
        pull="import numpy as np; PULLED_DATA=np.loadtxt(fname='$FILE_PATH')"
        REP.dump(value, relativePath='.', name='text.dat', dump=dump, pull=pull, replace=True)
        REP.dump(value, relativePath="folder1/folder2/folder3", name='folder3Pickled.pkl', replace=True)
        REP.dump(value, relativePath="folder1/archive1", name='archive1Pickled1', replace=True)
        REP.dump(value, relativePath="folder1/archive1", name='archive1Pickled2', replace=True)
        REP.dump(value, relativePath="folder1/archive1/archive2", name='archive2Pickled1', replace=True)
        
        # pull data
        data = REP.pull(relativePath='.', name='text.dat')
        print '\\nPulled text data --> %s'%str(data)
        
        data = REP.pull(relativePath="folder1/folder2/folder3", name='folder3Pickled.pkl')
        print '\\nPulled pickled data --> %s'%str(data)
        
        # update
        value = "This is an updated string"
        REP.update(value, relativePath='.', name='pickled')
        print '\\nUpdate pickled data to --> %s'%value
        
        data = REP.pull(relativePath='.', name='pickled')
        print '\\nPull updated pickled data --> %s'%str(data)

        # walk repository files
        print '\\nwalk repository files relative path'
        print '------------------------------------'
        for f in REP.walk_files_relative_path():
            print f
        
        # walk repository, directories
        print '\\nwalk repository directories relative path'
        print '------------------------------------------'
        for d in REP.walk_directories_relative_path():
            print d
        
        
        print '\\nRepository print -->'
        print REP
        
        print '\\nRepository representation -->'
        print repr(REP)
        
        print '\\nRepository to list -->'
        print  REP.get_list_representation()
        REP.create_package(path=None, name=None)
        
        # Try to load
        try:
            REP.load_repository(PATH)
        except:
            loadable = False
        finally:
            loadable = True
        print '\\nIs repository loadable -->',loadable 
        
        # remove all repo data
        REP.remove_repository(relatedFiles=True, relatedFolders=True)
        
        # check if there is a repository in path
        print "\\nIs path '%s' a repository --> %s"%(PATH, str(REP.is_repository(PATH)))


        
output
====== 

.. code-block:: pycon

        repository path --> None
        
        Is path 'C:\\Users\\aoun\\pyrepTest_canBeDeleted' a repository --> False
        
        Repository path --> C:\\Users\\aoun\\pyrepTest_canBeDeleted
        
        Pulled text data --> [ 0.5270431   0.6661849   0.06717668]
        
        Pulled pickled data --> [ 0.52704312  0.66618488  0.06717668]
        
        Update pickled data to --> This is an updated string
        Pull updated pickled data --> This is an updated string
        
        walk repository files relative path
        ------------------------------------
        pickled
        text.dat
        folder1\\archive1\\archive1Pickled1
        folder1\\archive1\\archive1Pickled2
        folder1\\archive1\\archive2\\archive2Pickled1
        folder1\\folder2\\folder3\\folder3Pickled.pkl
        
        walk repository directories relative path
        ------------------------------------------
        directory1
        folder1
        directory1\\directory2
        folder1\\archive1
        folder1\\folder2
        folder1\\archive1\\archive2
        folder1\\archive1\\archive2\\archive3
        folder1\\archive1\\archive2\\archive3\\archive3
        folder1\\folder2\\folder3
        
        Repository print -->
        C:\\Users\\aoun\\pyrepTest_canBeDeleted
          text.dat
          pickled
          \\directory1
            \\directory2
          \\folder1
            \\archive1
              archive1Pickled1
              archive1Pickled2
              \\archive2
                archive2Pickled1
                \\archive3
                  \\archive3
            \\folder2
              \\folder3
                folder3Pickled.pkl
        
        Repository representation -->
        Repository (Version 0.1.1)
        C:\\Users\\aoun\\pyrepTest_canBeDeleted:[text.dat,pickled] ; directory1:[] ; directory1\\directory2:[] ; folder1:[] ; folder1\\ar
        chive1:[archive1Pickled1,archive1Pickled2] ; folder1\\archive1\\archive2:[archive2Pickled1] ; folder1\\archive1\\archive2\ar
        chive3:[] ; folder1\\archive1\\archive2\\archive3\\archive3:[] ; folder1\\folder2:[] ; folder1\\folder2\\folder3:[folder3Pickle
        d]
        
        Repository to list -->
        ['C:\\Users\\aoun\\pyrepTest_canBeDeleted:[text.dat,pickled]', 'directory1:[]', 'directory1\\directory2:[]', 'folder1:[]', '
        folder1\\archive1:[archive1Pickled1,archive1Pickled2]', 'folder1\\archive1\\archive2:[archive2Pickled1]', 'folder1\\arch
        ive1\\archive2\\archive3:[]', 'folder1\\archive1\\archive2\\archive3\\archive3:[]', 'folder1\\folder2:[]', 'folder1\\fol
        der2\\folder3:[folder3Pickled.pkl]']
        
        Is repository loadable --> True
        
        Is path 'C:\\Users\\aoun\\pyrepTest_canBeDeleted' a repository --> False


Repository main module:
=======================
"""

# standard distribution imports
import os
import time
import uuid
import traceback
import warnings
import tarfile
import tempfile
import shutil
import inspect
from datetime import datetime
from functools import wraps
import copy
try:
    import cPickle as pickle
except:
    import pickle

# import pylocker
from pylocker import Locker

# pyrep imports
from __pkginfo__ import __version__
    
# set warnings filter to always
warnings.simplefilter('always')

#### Define decorators ###
def path_required(func):
    """Decorate methods when repository path is required."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.path is None:
            warnings.warn('Must load or initialize the repository first !')
            return
        return func(self, *args, **kwargs)
    return wrapper

def hide_dict_required(func):
    """Decorate methods when hiding repository dictionnary methods is required."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.DICT_HIDE:
            traceback.print_stack()
            warnings.warn("Repository class '%s' method '%s' is hidden!\n args: %s\n kwargs: %s"%(self.__class__.__name__,func.__name__, args, kwargs))
            return
        return func(self, *args, **kwargs)
    return wrapper

def acquire_lock(func):
    """Decorate methods when locking repository is required."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        e = None
        with self.locker as r:
            # get the result
            acquired, code, _  = r
            if acquired:
                try:
                    r = func(self, *args, **kwargs)
                except Exception as e:
                    pass
            else:
                warnings.warn("code %s. Unable to aquire the lock when calling '%s'. You may try again!"%(code,func.__name__) )
                r = None
        # raise error after exiting with statement and releasing the lock!
        if e is not None:
            raise Exception(e)
        return r
    return wrapper

def sync_required(func):
    """Decorate methods when synchronizing repository is required."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self._keepSynchronized:
            r = func(self, *args, **kwargs)
        else:
            state = self._load_state()
            if state is None:
                r = func(self, *args, **kwargs)
            elif state == self.state:
                r = func(self, *args, **kwargs)
            else:
                warnings.warn("Repository at '%s' is out of date. Need to load it again to avoid conflict."%self.path)
                r = None
        return r
    return wrapper
    

### get pickling errors method ###
def get_pickling_errors(obj, seen=None):
    """Investigate pickling errors."""
    if seen == None:
        seen = []
    if hasattr(obj, "__getstate__"):
        state = obj.__getstate__()
    #elif hasattr(obj, "__dict__"):
    #    state = obj.__dict__
    else:
        return None
    #try:
    #    state = obj.__getstate__()
    #except AttributeError as e:
    #    #state = obj.__dict__
    #    return str(e)
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
            pickle.dumps(state[i], protocol=pickle.HIGHEST_PROTOCOL)
        except pickle.PicklingError as e:
            if not state[i] in seen:
                seen.append(state[i])
                result[i]=get_pickling_errors(state[i],seen)
    return result
    
    
class Repository(dict):
    """
    This is a pythonic way to organize dumping and pulling python objects 
    or any type of files to a folder or directory that we call repository. 
    Any directory can be a repository, it suffices to initialize a Repository 
    instance in a directory to start dumping and pulling object into it. 
    Any directory that has .pyrepinfo binary file in it is theoretically a pyrep Repository.
    
    :Parameters:
        #. repo (None, path, Repository): This is used to initialize a Repository instance.\n
           If None, Repository is initialized but not assigned to any directory.\n
           If Path, Repository is loaded from directory path unless directory is not a repository and error will be raised.\n
           If Repository, current instance will cast the given Repository instance.\n
        #. ACID (boolean): Whether to ensure the ACID (Atomicity, Consistency, Isolation, Durability) 
           properties of the repository upon dumping a file. This is ensured by dumping the file in
           a temporary path first and then moving it to the desired path.
    """
    __DICT_HIDE = True 
    def __init__(self, repo=None, ACID=True):
        self.__locker = Locker(filePath=None, lockPass=str(uuid.uuid1()),lockPath='.pyreplock')
        self.__path   = None
        self.__info   = None
        self.__state  = time.time()
        self._keepSynchronized = True
        self.__reset_repository()
        self.__cast(repo)
        self.__DICT_HIDE = True
        # set properties
        self.set_ACID(ACID=ACID)
    
    #def __getstate__(self):
    #    state = {}
    #    for k, v in self.__dict__.items():
    #        if k in ('_Repository__locker',):
    #            v = None
    #        state[k] = v
    #    return state
        
    def __str__(self):
        if self.__path is None:
            return ""
        string = os.path.normpath(self.__path)
        # walk files
        leftAdjust = "  "
        for file in dict.__getitem__(self, 'files').keys():
            string += "\n"
            string += leftAdjust
            string += file
            #string += " ("+dict.__getitem__(self, 'files')[file]['timestamp']+")"
        # walk directories
        for directory in sorted(list(self.walk_directories_relative_path())):
            # split directory path
            splitPath = directory.split(os.sep)
            # get left space
            leftAdjust = ''.join(['  '*(len(item)>0) for item in splitPath])
            # get directory info
            dirInfoDict, errorMessage = self.get_directory_info(directory)
            assert dirInfoDict is not None, errorMessage
            # append directories to representation
            string += "\n"
            string += leftAdjust
            string += os.sep+str(splitPath[-1])
            #string += " ("+dirInfoDict['timestamp']+")"
            # append files to representation
            leftAdjust += "  "
            for file in dict.__getitem__(dirInfoDict, 'files').keys():
                string += "\n"
                string += leftAdjust
                string += file
                #string += " ("+dict.__getitem__(dirInfoDict, 'files')[file]['timestamp']+")"
        return string    
    
    def __repr__(self):
        repr = self.__class__.__name__+" (Version "+str(self.version)+")"
        if self.__path is None:
            return repr
        repr += '\n'
        lrepr = self.get_list_representation()
        repr += " ; ".join(lrepr)
        return repr 
        
    @hide_dict_required
    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
    
    @hide_dict_required
    def __getitem__(self, key):
        dict.__getitem__(self, key)
     
    @hide_dict_required
    def keys(self, *args, **kwargs):
        """Keys is a locked method and therefore behave as a private one that is only callable from within the class definition."""
        return dict.keys(self)
    
    @hide_dict_required
    def values(self, *args, **kwargs):
        """values is a locked method and therefore behave as a private one that is only callable from within the class definition."""
        return dict.values(self)
        
    @hide_dict_required
    def items(self, *args, **kwargs):
        """items is a locked method and therefore behave as a private one that is only callable from within the class definition."""
        return dict.items(self)
    
    @hide_dict_required
    def pop(self, *args, **kwargs):
        """pop is a locked method and modified to be a private method only callable from within the instance."""
        return dict.pop(self, *args, **kwargs)
    
    @hide_dict_required
    def update(self, *args, **kwargs):
        """update is a locked method and therefore behave as a private one that is only callable from within the class definition."""
        return dict.pop(self, *args, **kwargs)
    
    @hide_dict_required
    def popitem(self, *args, **kwargs):
        """popitem is a locked method and therefore behave as a private one that is only callable from within the class definition."""
        return dict.popitem(self, *args, **kwargs)
    
    @hide_dict_required
    def viewkeys(self, *args, **kwargs):
        """viewkeys is a locked method and therefore behave as a private one that is only callable from within the class definition."""
        return dict.viewkeys(self, *args, **kwargs)
    
    @hide_dict_required
    def viewvalues(self, *args, **kwargs):
        """viewvalues is a locked method and therefore behave as a private one that is only callable from within the class definition."""
        return viewvalues.viewkeys(self, *args, **kwargs)  
        
    def __cast(self, repo):
        if repo is None:
            return
        if isinstance(repo, Repository):
            self.__reset_repository()
            self.__update_repository(repo)
        elif isinstance(repo, basestring):
            repo = str(repo)
            self.load_repository(repo)
        else:
            raise Exception("If not None, repo must be a Repository instance or a path. '%s' is given"%str(repo))
    
    def __reset_id(self):
        dict.__setitem__(self, "__uuid__", str(uuid.uuid1()))
    
    def __reset_version(self):
        dict.__setitem__(self, "__version__", __version__)
    
    def __reset_repository(self):
        self.__reset_version()
        self.__reset_id()
        # set directories and files dictionaries
        dict.__setitem__(self, "directories", {})
        dict.__setitem__(self, "files",       {})
            
    def __update_repository(self, repo):
        assert isinstance(repo, Repository), "repository must be a Repository instance"
        if repo.version > self.version:
            warnings.warn("Unable to update Repository of currently installed pyrep version %i to pyrep Repository version %i !"%(self.version, repo.version))
            return
        dict.update(self, repo)
        self.__path = repo.path
        self.__info = repo.info
        # update locker
        lp = '.pyreplock'
        if self.__path is not None:
            lp = os.path.join(self.__path,lp)
        self.__locker.set_lock_path(lp)
        self.__locker.set_lock_pass(str(uuid.uuid1()))
    
    def _load_state(self):
        repoTimePath = os.path.join(self.__path, ".pyrepstate")
        # get state
        state = None
        if os.path.isfile(repoTimePath):
            try:
                state = float( open(repoTimePath).readline().strip() )
            except Exception as e:
                warnings.warn("unable to open repository time stamp for reading (%s)"%e)
                state = None
        return state
       
    def _get_or_create_state(self, forceCreate=False):
        create = forceCreate
        repoTimePath = os.path.join(self.__path, ".pyrepstate")
        # get state
        if not create:
            state = self._load_state()
            if state is None:
                create = True
        # create state
        if create:
            try:
                state = time.time()
                with open(repoTimePath, 'w') as fdtime:
                    fdtime.write( '%.6f'%state  )
                    fdtime.flush()
                    os.fsync(fdtime.fileno())
            except Exception as e:
                raise Exception("unable to open repository time stamp for saving (%s)"%e) 
        # return
        return state
        
    @property
    def state(self):
        """Repository state."""
        return self.__state
        
    @property
    def DICT_HIDE(self):
        """Python dictionary methods hide flag value."""
        return self.__DICT_HIDE 
            
    @property
    def locker(self):
        """Repository locker manager."""
        return self.__locker
        
    @property
    def path(self):
        """The repository instance path which points to the folder and 
        directory where .pyrepinfo is."""
        return self.__path
    
    @property
    def info(self):
        """The unique user defined information of this repository instance."""
        return copy.deepcopy( self.__info )
    
    @property
    def version(self):
        """The version of this repository."""
        return dict.__getitem__(self,"__version__")
        
    @property
    def id(self):
        """The universally unique id of this repository."""
        return dict.__getitem__(self,"__uuid__")
    
    def set_ACID(self, ACID):
        """
        Set the gobal ACID poperty of the repository.
    
        :parameters:
            #. ACID (boolean): Whether to ensure the ACID (Atomicity, Consistency, Isolation, Durability) 
               properties of the repository upon dumping a file. This is ensured by dumping the file in
               a temporary path first and then moving it to the desired path.
               
        """
        assert isinstance(ACID, bool), "ACID property must be boolean"
        self.__ACID = ACID  
          
    def get_list_representation(self):
        """
        Gets a representation of the Repository content in a list of directories(files) format.
        
        :Returns:
            #. repr (list): The list representation of the Repository content.
        """
        if self.__path is None:
            return []
        repr = [ self.__path+":["+','.join(dict.__getitem__(self, 'files').keys())+']' ]
        # walk directories
        for directory in sorted(list(self.walk_directories_relative_path())):
            directoryRepr = os.path.normpath(directory)
            # get directory info
            dirInfoDict, errorMessage = self.get_directory_info(directory)
            assert dirInfoDict is not None, errorMessage
            directoryRepr += ":["+','.join( dict.__getitem__(dirInfoDict, 'files').keys())+']'
            repr.append(directoryRepr)
        return repr
        
    def walk_files_relative_path(self, relativePath=""):
        """
        Walk the repository and yield all found files relative path joined with file name.
        
        :parameters:
            #. relativePath (str): The relative path from which start the walk.
        """
        def walk_files(directory, relativePath):
            directories = dict.__getitem__(directory, 'directories')
            files       = dict.__getitem__(directory, 'files')
            for f in sorted(files):
                yield os.path.join(relativePath, f)
            for k in sorted(dict.keys(directories)):
                path = os.path.join(relativePath, k)
                dir  = directories.__getitem__(k)
                for e in walk_files(dir, path):
                    yield e
        dir, errorMessage = self.get_directory_info(relativePath)
        assert dir is not None, errorMessage
        return walk_files(dir, relativePath='')
    
    def walk_files_info(self, relativePath=""):
        """
        Walk the repository and yield tuples as the following:\n 
        (relative path to relativePath joined with file name, file info dict).
        
        :parameters:
            #. relativePath (str): The relative path from which start the walk.
        """
        def walk_files(directory, relativePath):
            directories = dict.__getitem__(directory, 'directories')
            files       = dict.__getitem__(directory, 'files')
            for fname in sorted(files.keys()):
                info = dict.__getitem__(files,fname)
                yield os.path.join(relativePath, fname), info
            for k in sorted(dict.keys(directories)):
                path = os.path.join(relativePath, k)
                dir  = dict.__getitem__(directories, k)
                for e in walk_files(dir, path):
                    yield e
        dir, errorMessage = self.get_directory_info(relativePath)
        assert dir is not None, errorMessage
        return walk_files(dir, relativePath='')
    
    def walk_directories_relative_path(self, relativePath=""):
        """
        Walk repository and yield all found directories relative path
        
        :parameters:
            #. relativePath (str): The relative path from which start the walk.
        """
        def walk_directories(directory, relativePath):
            directories = dict.__getitem__(directory, 'directories')
            dirNames = dict.keys(directories)
            for d in sorted(dirNames):
                yield os.path.join(relativePath, d)
            for k in sorted(dict.keys(directories)):
                path = os.path.join(relativePath, k)
                dir  = dict.__getitem__(directories, k)
                for e in walk_directories(dir, path):
                    yield e
        dir, errorMessage = self.get_directory_info(relativePath)
        assert dir is not None, errorMessage
        return walk_directories(dir, relativePath='')
    
    def walk_directories_info(self, relativePath=""):
        """
        Walk repository and yield all found directories relative path.
        
        :parameters:
            #. relativePath (str): The relative path from which start the walk.
        """
        def walk_directories(directory, relativePath):
            directories = dict.__getitem__(directory, 'directories')
            for fname in sorted(directories.keys()):
                info = dict.__getitem__(directories,fname)
                yield os.path.join(relativePath, fname), info
            for k in sorted(dict.keys(directories)):
                path = os.path.join(relativePath, k)
                dir  = dict.__getitem__(directories, k)
                for e in walk_directories(dir, path):
                    yield e
        dir, errorMessage = self.get_directory_info(relativePath)
        assert dir is not None, errorMessage
        return walk_directories(dir, relativePath='')
        
    def walk_directory_files_relative_path(self, relativePath=""):
        """
        Walk a certain directory in repository and yield all found 
        files relative path joined with file name.
        
        :parameters:
            #. relativePath (str): The relative path of the directory.
        """
        # get directory info dict
        relativePath = os.path.normpath(relativePath)
        dirInfoDict, errorMessage = self.get_directory_info(relativePath)
        assert dirInfoDict is not None, errorMessage
        for fname in dict.__getitem__(dirInfoDict, "files").keys():
            yield os.path.join(relativePath, fname)
    
    def walk_directory_files_info(self, relativePath=""):
        """
        Walk a certain directory in repository and yield tuples as the following:\n
        (relative path joined with file name, file info dict).
        
        :parameters:
            #. relativePath (str): The relative path of the directory.
        """
        # get directory info dict
        relativePath = os.path.normpath(relativePath)
        dirInfoDict, errorMessage = self.get_directory_info(relativePath)
        assert dirInfoDict is not None, errorMessage
        for fname, info in dict.__getitem__(dirInfoDict, "files").items():
            yield os.path.join(relativePath, fname), info
        
    def walk_directory_directories_relative_path(self, relativePath=""):
        """
        Walk a certain directory in repository and yield all found directories relative path.
        
        :parameters:
            #. relativePath (str): The relative path of the directory.
        """
        # get directory info dict
        errorMessage = ""
        relativePath = os.path.normpath(relativePath)
        dirInfoDict, errorMessage = self.get_directory_info(relativePath)
        assert dirInfoDict is not None, errorMessage
        for dname in dict.__getitem__(dirInfoDict, "directories").keys():
            yield os.path.join(relativePath, dname)
    
    def walk_directory_directories_info(self, relativePath=""):
        """
        Walk a certain directory in repository and yield tuples as the following:\n 
        (relative path joined with directory name, file info dict).
        
        :parameters:
            #. relativePath (str): The relative path of the directory.
        """
        # get directory info dict
        relativePath = os.path.normpath(relativePath)
        dirInfoDict, errorMessage = self.get_directory_info(relativePath)
        assert dirInfoDict is not None, errorMessage
        for fname, info in dict.__getitem__(dirInfoDict, "directories").items():
            yield os.path.join(relativePath, fname), info
    
    @acquire_lock
    def synchronize(self, verbose=False):
        """
        Synchronizes the Repository information with the directory.
        All registered but missing files and directories in the directory, 
        will be automatically removed from the Repository.
        
        :parameters:
            #. verbose (boolean): Whether to be warn and inform about any abnormalities.
        """
        if self.__path is None:
            return
        # walk directories
        for dirPath in sorted(list(self.walk_directories_relative_path())):
            realPath = os.path.join(self.__path, dirPath)
            # if directory exist
            if os.path.isdir(realPath): 
                continue             
            if verbose: warnings.warn("%s directory is missing"%realPath) 
            # loop to get dirInfoDict
            keys = dirPath.split(os.sep)
            dirInfoDict = self
            for idx in range(len(keys)-1):
                dirs = dict.get(dirInfoDict, 'directories', None)
                if dirs is None: break
                dirInfoDict = dict.get(dirs, keys[idx], None) 
                if dirInfoDict is None: break
            # remove dirInfoDict directory if existing
            if dirInfoDict is not None:   
                dirs = dict.get(dirInfoDict, 'directories', None)
                if dirs is not None:      
                    dict.pop( dirs, keys[-1], None ) 
        # walk files
        for filePath in sorted(list(self.walk_files_relative_path())):
            realPath = os.path.join(self.__path, filePath)
            # if file exists
            if os.path.isfile( realPath ):
                continue
            if verbose: warnings.warn("%s file is missing"%realPath) 
            # loop to get dirInfoDict
            keys = filePath.split(os.sep)
            dirInfoDict = self
            for idx in range(len(keys)-1):
                dirs = dict.get(dirInfoDict, 'directories', None)
                if dirs is None: break
                dirInfoDict = dict.get(dirs, keys[idx], None) 
                if dirInfoDict is None: break
            # remove dirInfoDict file if existing
            if dirInfoDict is not None:   
                files = dict.get(dirInfoDict, 'files', None)
                if files is not None:      
                    dict.pop( files, keys[-1], None ) 
    
    def load_repository(self, path):
        """
        Load repository from a directory path and update the current instance.
        
        :Parameters:
            #. path (string): The path of the directory from where to load the repository.
               If '.' or an empty string is passed, the current working directory will be used.
        
        :Returns:
             #. repository (pyrep.Repository): returns self repository with loaded data.
        """
        # try to open
        if path.strip() in ('','.'):
            path = os.getcwd()
        repoPath = os.path.realpath( os.path.expanduser(path) )
        if not self.is_repository(repoPath):
            raise Exception("no repository found in '%s'"%str(repoPath))
        # get pyrepinfo path
        repoInfoPath = os.path.join(repoPath, ".pyrepinfo")
        try:
            fd = open(repoInfoPath, 'rb')
        except Exception as e:
            raise Exception("unable to open repository file(%s)"%e)   
        # before doing anything try to lock repository 
        # can't decorate with @acquire_lock because this will point to old repository
        # path or to current working directory which might not be the path anyways
        L =  Locker(filePath=None, lockPass=str(uuid.uuid1()), lockPath=os.path.join(repoPath, ".pyreplock"))
        acquired, code = L.acquire_lock()
        # check if acquired.
        if not acquired:
            warnings.warn("code %s. Unable to aquire the lock when calling 'load_repository'. You may try again!"%(code,) )
            return
        try:
            DH = Repository.__DICT_HIDE
            Repository.__DICT_HIDE = False
            # unpickle file
            try:
                repo = pickle.load( fd )
            except Exception as e:
                fd.close()
                Repository.__DICT_HIDE = DH
                raise Exception("unable to pickle load repository (%s)"%e)  
            finally:
                fd.close()
                Repository.__DICT_HIDE = DH
            # check if it's a PyrepInfo instance
            if not isinstance(repo, Repository): 
                raise Exception(".pyrepinfo in '%s' is not a repository instance."%s)  
            else:
                # update info path
                self.__reset_repository()
                self.__update_repository(repo)
                self.__path = repoPath
            # set timestamp
            self.__state = self._get_or_create_state()
        except Exception as e:
            L.release_lock()
            raise Exception(e)  
        finally:
            L.release_lock()
        # set loaded repo locker path to L because repository have been moved to another directory
        self.__locker = L
        # return 
        return self
    
    def connect(self, path):
        """Alias to load_repository"""
        return self.load_repository(path)
    
    def create_repository(self, path, info=None, verbose=True): 
        """
        create a repository in a directory.
        This method insures the creation of the directory in the system if it is missing.\n
        
        **N.B. This method erases existing pyrep repository in the path but not the repository files.** 
        
        :Parameters:
            #. path (string): The real absolute path where to create the Repository.
               If '.' or an empty string is passed, the current working directory will be used.
            #. info (None, object): Any information that can identify the repository.
            #. verbose (boolean): Whether to be warn and informed about any abnormalities.
        """
        try:
            info = copy.deepcopy( info )
        except:
            raise Exception("Repository info must be a copyable python object.") 
        # get real path
        if path.strip() in ('','.'):
            path = os.getcwd()
        realPath = os.path.realpath( os.path.expanduser(path) )
        # create directory if not existing
        if not os.path.isdir(realPath):
            os.makedirs(realPath)
        self.__path = realPath
        self.__info = info
        # reset if replace is set to True
        if self.is_repository(realPath):
            if verbose:
                warnings.warn("A pyrep Repository already exists in the given path '%s' and therefore it has been erased and replaced by a fresh repository."%path)
        # reset repository
        self.__reset_repository()  
        # update locker because normally this is done in __update_repository method
        lp = '.pyreplock'
        if self.__path is not None:
            lp = os.path.join(self.__path,lp)
        self.__locker.set_lock_path(lp)
        self.__locker.set_lock_pass(str(uuid.uuid1()))      
        # save repository
        self.save()
                   
    def get_repository(self, path, info=None, verbose=True):
        """
        Create a repository at given real path or load any existing one.
        This method insures the creation of the directory in the system if it is missing.\n
        Unlike create_repository, this method doesn't erase any existing repository 
        in the path but loads it instead.
        
        **N.B. On some systems and some paths, creating a directory may requires root permissions.**  
        
        :Parameters:
            #. path (string): The real absolute path where to create the Repository.
               If '.' or an empty string is passed, the current working directory will be used.
            #. info (None, object): Any information that can identify the repository.
            #. verbose (boolean): Whether to be warn and informed about any abnormalities.
        """
        # get real path
        if path.strip() in ('','.'):
            path = os.getcwd()
        realPath = os.path.realpath( os.path.expanduser(path) )
        # create directory if not existing
        if not os.path.isdir(realPath):
            os.makedirs(realPath)
        # create Repository
        if not self.is_repository(realPath):
            self.create_repository(realPath, info=info, verbose=verbose)
        else:
            self.load_repository(realPath)
 
    def remove_repository(self, path=None, relatedFiles=False, relatedFolders=False, verbose=True):
        """
        Remove .pyrepinfo file from path if exists and related files and directories 
        when respective flags are set to True. 
        
        :Parameters:
            #. path (None, string): The path of the directory where to remove an existing repository.
               If None, current repository is removed if initialized.
            #. relatedFiles (boolean): Whether to also remove all related files from system as well.
            #. relatedFolders (boolean): Whether to also remove all related directories from system as well.
               Directories will be removed only if they are left empty after removing the files.
            #. verbose (boolean): Whether to be warn and informed about any abnormalities.
        """
        if path is not None:
            realPath = os.path.realpath( os.path.expanduser(path) )
        else:
            realPath = self.__path
        if realPath is None:
            if verbose: warnings.warn('path is None and current Repository is not initialized!')
            return
        if not self.is_repository(realPath):
            if verbose: warnings.warn("No repository found in '%s'!"%realPath)
            return
        # check for security  
        if realPath == os.path.realpath('/..') :
            if verbose: warnings.warn('You are about to wipe out your system !!! action aboarded')
            return
        # get repo
        if path is not None:
            repo = Repository()
            repo.load_repository(realPath)
        else:
            repo = self
        # delete files
        if relatedFiles:
            for relativePath in repo.walk_files_relative_path():
                realPath = os.path.join(repo.path, relativePath)
                if not os.path.isfile(realPath):
                    continue
                if not os.path.exists(realPath):
                    continue
                os.remove( realPath )
        # delete directories
        if relatedFolders:
            for relativePath in reversed(list(repo.walk_directories_relative_path())):
                realPath = os.path.join(repo.path, relativePath)
                # protect from wiping out the system
                if not os.path.isdir(realPath):
                    continue
                if not os.path.exists(realPath):
                    continue
                if not len(os.listdir(realPath)):
                    os.rmdir( realPath )
        # delete repository    
        os.remove( os.path.join(repo.path, ".pyrepinfo" ) )
        for fname in (".pyrepstate", ".pyreplock"):
            p = os.path.join(repo.path, fname )
            if os.path.exists( p ):
                os.remove( p ) 
        # remove main directory if empty
        if os.path.isdir(repo.path):
            if not len(os.listdir(repo.path)):
                os.rmdir( repo.path )
        # reset repository
        repo.__reset_repository() 
        

    @path_required
    @acquire_lock
    @sync_required
    def save(self):
        """ Save repository .pyrepinfo to disk. """
        # open file
        repoInfoPath = os.path.join(self.__path, ".pyrepinfo")
        try:
            fdinfo = open(repoInfoPath, 'wb')
        except Exception as e:
            raise Exception("unable to open repository info for saving (%s)"%e)   
        # save repository
        try:
            pickle.dump( self, fdinfo, protocol=pickle.HIGHEST_PROTOCOL )
        except Exception as e:
            fdinfo.flush()
            os.fsync(fdinfo.fileno())
            fdinfo.close()
            raise Exception( "Unable to save repository info (%s)"%e )
        finally:
            fdinfo.flush()
            os.fsync(fdinfo.fileno())
            fdinfo.close()
        # save timestamp
        repoTimePath = os.path.join(self.__path, ".pyrepstate")
        try:
            self.__state = time.time()
            with open(repoTimePath, 'w') as fdtime:
                fdtime.write( '%.6f'%self.__state  )
                fdtime.flush()
                os.fsync(fdtime.fileno())
        except Exception as e:
            raise Exception("unable to open repository time stamp for saving (%s)"%e)
    
    @path_required
    def create_package(self, path=None, name=None, mode=None):
        """
        Create a tar file package of all the repository files and directories. 
        Only files and directories that are stored in the repository info 
        are stored in the package tar file.
        
        **N.B. On some systems packaging requires root permissions.**  
        
        :Parameters:
            #. path (None, string): The real absolute path where to create the package.
               If None, it will be created in the same directory as the repository
               If '.' or an empty string is passed, the current working directory will be used.
            #. name (None, string): The name to give to the package file
               If None, the package directory name will be used with the appropriate extension added.
            #. mode (None, string): The writing mode of the tarfile.
               If None, automatically the best compression mode will be chose.
               Available modes are ('w', 'w:', 'w:gz', 'w:bz2')
        """
        # check mode
        assert mode in (None, 'w', 'w:', 'w:gz', 'w:bz2'), 'unkown archive mode %s'%str(mode)
        if mode is None:
            mode = 'w:bz2'
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
        # save repository
        self.save()
        # create tar file
        tarfilePath = os.path.join(root, name)
        try:
            tarHandler = tarfile.TarFile.open(tarfilePath, mode=mode)
        except Exception as e:
            raise Exception("Unable to create package (%s)"%e)
        # walk directory and create empty directories
        for directory in sorted(list(self.walk_directories_relative_path())):
            t = tarfile.TarInfo( directory )
            t.type = tarfile.DIRTYPE
            tarHandler.addfile(t)
        # walk files and add to tar
        for file in self.walk_files_relative_path():
            tarHandler.add(os.path.join(self.__path,file), arcname=file)
        # save repository .pyrepinfo
        tarHandler.add(os.path.join(self.__path,".pyrepinfo"), arcname=".pyrepinfo")
        # close tar file
        tarHandler.close()            
            
    def is_repository(self, path):
        """
        Check if there is a Repository in path. 
        
        :Parameters:
            #. path (string): The real path of the directory where to check if there is a repository.
        
        :Returns:
            #. result (boolean): Whether its a repository or not.
        """
        realPath = os.path.realpath( os.path.expanduser(path) )
        if not os.path.isdir(realPath):
            return False
        if ".pyrepinfo" not in os.listdir(realPath):
            return False
        return True
        
    def get_directory_info(self, relativePath): 
        """
        get directory info from the Repository.
        
        :Parameters:
            #. relativePath (string): The relative to the repository path of the directory.
        
        :Returns:
            #. info (None, dictionary): The directory information dictionary.
               If None, it means an error has occurred.
            #. error (string): The error message if any error occurred.
        """
        relativePath = os.path.normpath(relativePath)
        # if root directory
        if relativePath in ('','.'):
            return self, ""
        currentDir  = self.__path
        dirInfoDict = self    
        for dir in relativePath.split(os.sep):
            dirInfoDict = dict.__getitem__(dirInfoDict, "directories")   
            currentDir = os.path.join(currentDir, dir)
            # check if path exists
            if not os.path.exists(currentDir):
                return None,  "directory '%s' is not found"%currentDir
            val = dirInfoDict.get(dir, None)
            # check if directory is registered in repository
            if val is None:
                return None,  "directory '%s' is not registered in PyrepInfo"%currentDir   
            dirInfoDict = val       
        return dirInfoDict, ""
    
    def get_parent_directory_info(self, relativePath): 
        """
        get parent directory info of a file or directory from the Repository.
        
        :Parameters:
            #. relativePath (string): The relative to the repository path of the file or directory of which the parent directory info is requested.
        
        :Returns:
            #. info (None, dictionary): The directory information dictionary.
               If None, it means an error has occurred.
            #. error (string): The error message if any error occurred.
        """
        relativePath = os.path.normpath(relativePath)
        # if root directory
        if relativePath in ('','.'):
            return self, "relativePath is empty pointing to the repostitory itself."
        # split path
        parentDirPath, _ = os.path.split(relativePath)
        # get parent directory info
        return self.get_directory_info(parentDirPath)

    def get_file_info(self, relativePath, name=None): 
        """
        get file information dict from the repository given its relative path and name.
        
        :Parameters:
            #. relativePath (string): The relative to the repository path of the directory where the file is.
            #. name (string): The file name.
               If None is given, name will be split from relativePath.
               
        :Returns:
            #. info (None, dictionary): The file information dictionary.
               If None, it means an error has occurred.
            #. errorMessage (string): The error message if any error occurred.
        """
        # normalize relative path and name
        relativePath = os.path.normpath(relativePath)
        if relativePath == '.':
            relativePath = ''
            assert name != '.pyrepinfo', "'.pyrepinfo' can't be a file name."
        if name is None:
            assert len(relativePath), "name must be given when relative path is given as empty string or as a simple dot '.'"
            relativePath,name = os.path.split(relativePath)
        # initialize message
        errorMessage = ""
        # get directory info
        dirInfoDict, errorMessage = self.get_directory_info(relativePath)
        if dirInfoDict is None:
            return None, errorMessage
        # get file info
        fileInfo = dict.__getitem__(dirInfoDict, "files").get(name, None)
        if fileInfo is None:
            errorMessage = "file %s does not exist in relative path '%s'"%(name, relativePath)
        return fileInfo, errorMessage
    
    def get_file_info_by_id(self, id): 
        """
        Given an id, get the corresponding file info as the following:\n
        (relative path joined with file name, file info dict)
        
        Parameters:
            #. id (string): The file unique id string.
        
        :Returns:
            #. relativePath (string): The file relative path joined with file name.
               If None, it means file was not found.
            #. info (None, dictionary): The file information dictionary.
               If None, it means file was not found.
        """
        for path, info in self.walk_files_info():
            if info['id']==id:
                return path, info
        # none was found
        return None, None
    
    def get_file_relative_path_by_id(self, id): 
        """
        Given an id, get the corresponding file info relative path joined with file name.
        
        Parameters:
            #. id (string): The file unique id string.
        
        :Returns:
            #. relativePath (string): The file relative path joined with file name.
               If None, it means file was not found.
        """
        for path, info in self.walk_files_info():
            if info['id']==id:
                return path
        # none was found
        return None
    
    def get_file_relative_path_by_name(self, name, skip=0): 
        """
        Get file relative path given the file name. If file name is redundant in different 
        directories in the repository, this method ensures to return all or some of the 
        files according to skip value.
        
        Parameters:
            #. name (string): The file name.
            #. skip (None, integer): As file names can be identical, skip determines 
               the number of satisfying files name to skip before returning.\n
               If None is given, a list of all files relative path will be returned.
        
        :Returns:
            #. relativePath (string, list): The file relative path.
               If None, it means file was not found.\n
               If skip is None a list of all found files relative paths will be returned.
        """
        if skip is None:
            paths = []
        else:
            paths = None
        for path, info in self.walk_files_info():
            _, n = os.path.split(path)
            if n==name:
                if skip is None:
                    paths.append(path)
                elif skip>0:
                    skip -= 1
                else:
                    paths = path
                    break
        return paths
        
    def get_file_info_by_name(self, name, skip=0): 
        """
        Get file information tuple given the file name. If file name is redundant in different 
        directories in the repository, this method ensures to return all or some of the 
        files infos according to skip value.
        
        Parameters:
            #. name (string): The file name.
            #. skip (None, integer): As file names can be identical, skip determines 
               the number of satisfying files name to skip before returning.\n
               If None is given, a list of all files relative path will be returned.
        
        :Returns:
            #. relativePath (string, list): The file relative path joined with file name.
               If None, it means file was not found.\n
               If skip is None a list of all found files relative paths will be returned.
            #. info (None, dictionary, list): The file information dictionary.
               If None, it means file was not found.\n
               If skip is None a list of all found files info dicts will be returned.
        """
        if skip is None:
            paths = []
            infos = []
        else:
            paths = None
            infos = None
        for path, info in self.walk_files_info():
            _, n = os.path.split(path)
            if n==name:
                if skip is None:
                    paths.append(path)
                    infos.append(info)
                elif skip>0:
                    skip -= 1
                else:
                    paths = path
                    infos = info
                    break
        return paths, infos
    
    @acquire_lock
    @sync_required
    def add_directory(self, relativePath, info=None):
        """
        Adds a directory in the repository and creates its 
        attribute in the Repository with utc timestamp.
        It insures adding all the missing directories in the path.
        
        :Parameters:
            #. relativePath (string): The relative to the repository path of the directory to add in the repository.
            #. info (None, string, pickable object): Any random info about the folder.
        
        :Returns:
            #. info (dict): The directory info dict.
        """
        path = os.path.normpath(relativePath)
        # create directories
        currentDir  = self.path
        #currentDict = dict.__getitem__(self,"directories")
        currentDict = self
        if path in ("","."):
            return currentDict
        save = False
        for dir in path.split(os.sep):
            dirPath = os.path.join(currentDir, dir)
            # create directory
            if not os.path.exists(dirPath):
                 os.mkdir(dirPath)
            # create dictionary key
            currentDict = dict.__getitem__(currentDict, "directories")
            if currentDict.get(dir, None) is None:    
                save = True
                currentDict[dir] = {"directories":{}, "files":{}, 
                                    "timestamp":datetime.utcnow(),
                                    "id":str(uuid.uuid1()), 
                                    "info": info} # INFO MUST BE SET ONLY FOR THE LAST DIRECTORY
                                    
            currentDict = currentDict[dir]
            currentDir  = dirPath
        # save repository
        if save:
            self.save()
        # return currentDict
        return currentDict
    
    @acquire_lock
    @sync_required
    def remove_directory(self, relativePath, removeFromSystem=False):
        """
        Remove directory from repository.
        
        :Parameters:
            #. relativePath (string): The relative to the repository path of the directory to remove from the repository.
            #. removeFromSystem (boolean): Whether to also remove directory and all files from the system.\n
               Only files saved in the repository will be removed and empty left directories.
        """
        # get parent directory info
        relativePath = os.path.normpath(relativePath)
        parentDirInfoDict, errorMessage = self.get_parent_directory_info(relativePath)
        assert parentDirInfoDict is not None, errorMessage
        # split path
        path, name = os.path.split(relativePath)
        if dict.__getitem__(parentDirInfoDict, 'directories').get(name, None) is None:
            raise Exception("'%s' is not a registered directory in repository relative path '%s'"%(name, path))
        # remove from system
        if removeFromSystem:
            # remove files
            for rp in self.walk_files_relative_path(relativePath=relativePath):
                ap = os.path.join(self.__path, relativePath, rp)
                if not os.path.isfile(ap):
                    continue
                if not os.path.exists(ap):
                    continue
                if os.path.isfile(ap):
                    os.remove( ap )
            # remove directories
            for rp in self.walk_directories_relative_path(relativePath=relativePath):
                ap = os.path.join(self.__path, relativePath, rp)
                if not os.path.isdir(ap):
                    continue
                if not os.path.exists(ap):
                    continue
                if not len(os.listdir(ap)):
                    os.rmdir(ap)
        # pop directory from repo
        dict.__getitem__(parentDirInfoDict, 'directories').pop(name, None)
        ap = os.path.join(self.__path, relativePath)
        if not os.path.isdir(ap):
            if not len(os.listdir(ap)):
                os.rmdir(ap)
        # save repository
        self.save()
    
    @acquire_lock
    @sync_required
    def move_directory(self, relativePath, relativeDestination, replace=False, verbose=True):
        """
        Move a directory in the repository from one place to another. It insures moving all the
        files and subdirectories in the system.
        
        :Parameters:
            #. relativePath (string): The relative to the repository path of the directory to be moved.
            #. relativeDestination (string): The new relative to the repository path of the directory.
            #. replace (boolean): Whether to replace existing files with the same name in the new created directory. 
            #. verbose (boolean): Whether to be warn and informed about any abnormalities.
        """
        # normalize path
        relativePath    = os.path.normpath(relativePath)
        relativeDestination = os.path.normpath(relativeDestination)
        # get files and directories
        filesInfo = list( self.walk_files_info(relativePath=relativePath) )
        dirsPath  = list( self.walk_directories_relative_path(relativePath=relativePath) )
        dirInfoDict, errorMessage = self.get_directory_info(relativePath)
        assert dirInfoDict is not None, errorMessage
        # remove directory info only
        self.remove_directory(relativePath=relativePath, removeFromSystem=False)
        # create new relative path
        self.add_directory(relativeDestination)
        # move files
        for RP, info in filesInfo:
            source      = os.path.join(self.__path, relativePath, RP)
            destination = os.path.join(self.__path, relativeDestination, RP)
            # add directory
            newDirRP, fileName = os.path.split(os.path.join(relativeDestination, RP))
            dirInfoDict = self.add_directory( newDirRP )
            # move file
            if os.path.isfile(destination):
                if replace:
                    os.remove(destination)
                    if verbose:
                        warnings.warn("file '%s' is copied replacing existing one in destination '%s'."%(fileName, newDirRP))
                else:
                    if verbose:
                        warnings.warn("file '%s' is not copied because the same file exists in destination '%s'."%(fileName,destination))
                    continue                        
            os.rename(source, destination)
            # set file information
            dict.__getitem__(dirInfoDict, "files")[fileName] = info
        # save repository
        self.save()
    
    @acquire_lock
    @sync_required
    def rename_directory(self, relativePath, newName, replace=False, verbose=True):
        """
        Rename a directory in the repository. It insures renaming the directory in the system.
        
        :Parameters:
            #. relativePath (string): The relative to the repository path of the directory to be renamed.
            #. newName (string): The new directory name.
            #. replace (boolean): Whether to force renaming when new name exists in the system.
               It fails when new folder name is registered in repository.
            #. verbose (boolean): Whether to be warn and informed about any abnormalities.
        """
        # normalize path
        relativePath    = os.path.normpath(relativePath)
        parentDirInfoDict, errorMessage = self.get_parent_directory_info(relativePath)
        assert parentDirInfoDict is not None, errorMessage
        # split path
        parentDirPath, dirName = os.path.split(relativePath)
        # get real path
        realPath  = os.path.join(self.__path, relativePath)
        assert os.path.isdir( realPath ), "directory '%s' is not found in system"%realPath
        # check directory in repository
        assert dict.__getitem__(parentDirInfoDict, "directories").has_key(dirName), "directory '%s' is not found in repository relative path '%s'"%(dirName, parentDirPath)
        # assert directory new name doesn't exist in repository
        assert not dict.__getitem__(parentDirInfoDict, "directories").has_key(newName), "directory '%s' already exists in repository, relative path '%s'"%(newName, parentDirPath)
        # check new directory in system
        newRealPath = os.path.join(self.__path, parentDirPath, newName)
        if os.path.isdir( newRealPath ):
            if replace:
                shutil.rmtree(newRealPath)
                if verbose:
                    warnings.warn( "directory '%s' already exists found in system, it is therefore deleted."%newRealPath )
            else:
                raise Exception( "directory '%s' already exists in system"%newRealPath )
        # rename directory
        os.rename(realPath, newRealPath)
        dict.__setitem__( dict.__getitem__(parentDirInfoDict, "directories"),
                          newName,
                          dict.__getitem__(parentDirInfoDict, "directories").pop(dirName) )
        # save repository
        self.save()                  
    
    @acquire_lock
    @sync_required
    def rename_file(self, relativePath, name, newName, replace=False, verbose=True):
        """
        Rename a directory in the repository. It insures renaming the file in the system.
        
        :Parameters:
            #. relativePath (string): The relative to the repository path of the directory where the file is located.
            #. name (string): The file name.
            #. newName (string): The file new name.
            #. replace (boolean): Whether to force renaming when new folder name exists in the system.
               It fails when new folder name is registered in repository.
            #. verbose (boolean): Whether to be warn and informed about any abnormalities.
        """
        # normalize path
        relativePath = os.path.normpath(relativePath)
        if relativePath == '.':
            relativePath = ''
        dirInfoDict, errorMessage = self.get_directory_info(relativePath)
        assert dirInfoDict is not None, errorMessage
        # check directory in repository
        assert dict.__getitem__(dirInfoDict, "files").has_key(name), "file '%s' is not found in repository relative path '%s'"%(name, relativePath)
        # get real path
        realPath = os.path.join(self.__path, relativePath, name)
        assert os.path.isfile(realPath), "file '%s' is not found in system"%realPath
        # assert directory new name doesn't exist in repository
        assert not dict.__getitem__(dirInfoDict, "files").has_key(newName), "file '%s' already exists in repository relative path '%s'"%(newName, relativePath)
        # check new directory in system
        newRealPath = os.path.join(self.__path, relativePath, newName)
        if os.path.isfile( newRealPath ):
            if replace:
                os.remove(newRealPath)
                if verbose:
                    warnings.warn( "file '%s' already exists found in system, it is now replaced by '%s' because 'replace' flag is True."%(newRealPath,realPath) )
            else:
                raise Exception( "file '%s' already exists in system but not registered in repository."%newRealPath )
        # rename file
        os.rename(realPath, newRealPath)
        dict.__setitem__( dict.__getitem__(dirInfoDict, "files"),
                          newName,
                          dict.__getitem__(dirInfoDict, "files").pop(name) )
        # save repository
        self.save()
    
    @acquire_lock
    @sync_required
    def remove_file(self, relativePath, name=None, removeFromSystem=False):
        """
        Remove file from repository.
        
        :Parameters:
            #. relativePath (string): The relative to the repository path of the directory where the file should be dumped.
               If relativePath does not exist, it will be created automatically.
            #. name (string): The file name.
               If None is given, name will be split from relativePath.
            #. removeFromSystem (boolean): Whether to also remove directory and all files from the system.\n
               Only files saved in the repository will be removed and empty left directories.
        """
        # get relative path normalized
        relativePath = os.path.normpath(relativePath)
        if relativePath == '.':
            relativePath = ''
            assert name != '.pyrepinfo', "'.pyrepinfo' is not allowed as file name in main repository directory"
            assert name != '.pyrepstate', "'.pyrepstate' is not allowed as file name in main repository directory"
            assert name != '.pyreplock', "'.pyreplock' is not allowed as file name in main repository directory"
        if name is None:
            assert len(relativePath), "name must be given when relative path is given as empty string or as a simple dot '.'"
            relativePath, name = os.path.split(relativePath)
        # get file info dict
        dirInfoDict, errorMessage = self.get_directory_info(relativePath)
        assert dirInfoDict is not None, errorMessage
        # check directory in repository
        assert dict.__getitem__(dirInfoDict, "files").has_key(name), "file '%s' is not found in repository relative path '%s'"%(name, relativePath)
        # remove file from repo
        dict.__getitem__(dirInfoDict, "files").pop(name)
        # remove file from system
        if removeFromSystem: 
            ap = os.path.join(self.__path, relativePath, name )
            if os.path.isfile(ap):
                os.remove( ap )
        # save repository
        self.save()    
    
    @acquire_lock
    @sync_required
    def dump_copy(self, path, relativePath, name=None, 
                        description=None,
                        replace=False, verbose=False):
        """
        Copy an exisitng system file to the repository.
        attribute in the Repository with utc timestamp.
        
        :Parameters:
            #. path (str): The full path of the file to copy into the repository.
            #. relativePath (str): The relative to the repository path of the directory where the file should be dumped.
               If relativePath does not exist, it will be created automatically.
            #. name (string): The file name.
               If None is given, name will be split from path.
            #. description (None, string, pickable object): Any random description about the file.
            #. replace (boolean): Whether to replace any existing file with the same name if existing.
            #. verbose (boolean): Whether to be warn and informed about any abnormalities.
        """
        relativePath = os.path.normpath(relativePath)
        if relativePath == '.':
            relativePath = ''
        if name is None:
            _,name = os.path.split(path)
        # ensure directory added
        self.add_directory(relativePath)
        # ger real path
        realPath = os.path.join(self.__path, relativePath)
        # get directory info dict
        dirInfoDict, errorMessage = self.get_directory_info(relativePath)
        assert dirInfoDict is not None, errorMessage
        if dict.__getitem__(dirInfoDict, "files").has_key(name):
            if not replace:
                if verbose:
                    warnings.warn("a file with the name '%s' is already defined in repository dictionary info. Set replace flag to True if you want to replace the existing file"%(name))
                return
        # convert dump and pull methods to strings
        dump = "raise Exception(\"dump is ambiguous for copied file '$FILE_PATH' \")"
        pull = "raise Exception(\"pull is ambiguous for copied file '$FILE_PATH' \")"
        # dump file
        try:
            shutil.copyfile(path, os.path.join(realPath,name))
        except Exception as e:
            if verbose:
                warnings.warn(e)
            return
        # set info
        klass = None
        # save the new file to the repository
        dict.__getitem__(dirInfoDict, "files")[name] = {"dump":dump,
                                                        "pull":pull,
                                                        "timestamp":datetime.utcnow(),
                                                        "id":str(uuid.uuid1()),
                                                        "class": klass,
                                                        "description":description}
        # save repository
        self.save()
        
    @acquire_lock
    @sync_required
    def dump_file(self, value, relativePath, name=None, 
                        description=None, klass=None,
                        dump=None, pull=None, 
                        replace=False, ACID=None, verbose=False):
        """
        Dump a file using its value to the system and creates its 
        attribute in the Repository with utc timestamp.
        
        :Parameters:
            #. value (object): The value of a file to dump and add to the repository. It is any python object or file.
            #. relativePath (str): The relative to the repository path of the directory where the file should be dumped.
               If relativePath does not exist, it will be created automatically.
            #. name (string): The file name.
               If None is given, name will be split from relativePath.
            #. description (None, string, pickable object): Any random description about the file.
            #. klass (None, class): The dumped object class. If None is given 
               klass will be automatically set to the following value.__class__
            #. dump (None, string): The dumping method. 
               If None it will be set automatically to pickle and therefore the object must be pickleable.
               If a string is given, the string should include all the necessary imports 
               and a '$FILE_PATH' that replaces the absolute file path when the dumping will be performed.\n
               e.g. "import numpy as np; np.savetxt(fname='$FILE_PATH', X=value, fmt='%.6e')"
            #. pull (None, string): The pulling method. 
               If None it will be set automatically to pickle and therefore the object must be pickleable.
               If a string is given, the string should include all the necessary imports, 
               a '$FILE_PATH' that replaces the absolute file path when the dumping will be performed
               and finally a PULLED_DATA variable.\n
               e.g "import numpy as np; PULLED_DATA=np.loadtxt(fname='$FILE_PATH')"  
            #. replace (boolean): Whether to replace any existing file with the same name if existing.
            #. ACID (None, boolean): Whether to ensure the ACID (Atomicity, Consistency, Isolation, Durability) 
               properties of the repository upon dumping a file. This is ensured by dumping the file in
               a temporary path first and then moving it to the desired path.
               If None is given, repository ACID property will be used.
            #. verbose (boolean): Whether to be warn and informed about any abnormalities.
        """
        # check ACID
        if ACID is None:
            ACID = self.__ACID
        assert isinstance(ACID, bool), "ACID must be boolean"
        # check name and path
        relativePath = os.path.normpath(relativePath)
        if relativePath == '.':
            relativePath = ''
            assert name != '.pyrepinfo', "'.pyrepinfo' is not allowed as file name in main repository directory"
            assert name != '.pyrepstate', "'.pyrepstate' is not allowed as file name in main repository directory"
            assert name != '.pyreplock', "'.pyreplock' is not allowed as file name in main repository directory"
        if name is None:
            assert len(relativePath), "name must be given when relative path is given as empty string or as a simple dot '.'"
            relativePath,name = os.path.split(relativePath)
        # ensure directory added
        self.add_directory(relativePath)
        # get real path
        realPath = os.path.join(self.__path, relativePath)
        # get directory info dict
        dirInfoDict, errorMessage = self.get_directory_info(relativePath)
        assert dirInfoDict is not None, errorMessage
        if dict.__getitem__(dirInfoDict, "files").has_key(name):
            if not replace:
                if verbose:
                    warnings.warn("a file with the name '%s' is already defined in repository dictionary info. Set replace flag to True if you want to replace the existing file"%(name))
                return
        # convert dump and pull methods to strings
        if dump is None:
            dump="pickle.dump( value, open('$FILE_PATH', 'wb'), protocol=pickle.HIGHEST_PROTOCOL )"
        if pull is None:
            pull="PULLED_DATA = pickle.load( open(os.path.join( '$FILE_PATH' ), 'rb') )"
        # get savePath
        if ACID:
            #savePath = os.path.join(tempfile.gettempdir(), name)
            savePath = os.path.join(tempfile.gettempdir(), str(uuid.uuid1()))
        else:
            savePath = os.path.join(realPath,name)
        # dump file
        try:
            exec( dump.replace("$FILE_PATH", savePath.encode('string-escape')) ) 
        except Exception as e:
            message = "unable to dump the file (%s)"%e
            if 'pickle.dump(' in dump:
                message += '\nmore info: %s'%str(get_pickling_errors(value))
            raise Exception( message )
        # copy if ACID
        if ACID:
            try:
                shutil.copyfile(savePath, os.path.join(realPath,name))
            except Exception as e:
                os.remove(savePath)
                if verbose:
                    warnings.warn(e)
                return
            os.remove(savePath)
        # set info
        if klass is None and value is not None:
            klass = value.__class__
        if klass is not None:
            assert inspect.isclass(klass), "klass must be a class definition"
        # MUST TRY PICLKING KLASS TEMPORARILY FIRST
        # save the new file to the repository
        dict.__getitem__(dirInfoDict, "files")[name] = {"dump":dump,
                                                        "pull":pull,
                                                        "timestamp":datetime.utcnow(),
                                                        "id":str(uuid.uuid1()),
                                                        "class": klass,
                                                        "description":description}
        # save repository
        self.save()
    
    def dump(self, *args, **kwargs):
        """Alias to dump_file"""
        self.dump_file(*args, **kwargs)
    
    @acquire_lock
    @sync_required
    def update_file(self, value, relativePath, name=None, 
                          description=False, klass=False,
                          dump=False, pull=False, 
                          ACID=None, verbose=False):
        """
        Update the value and the utc timestamp of a file that is already in the Repository.\n
        If file is not registered in repository, and error will be thrown.\n
        If file is missing in the system, it will be regenerated as dump method is called.
        
        :Parameters:
            #. value (object): The value of the file to update. It is any python object or a file.
            #. relativePath (str): The relative to the repository path of the directory where the file should be dumped.
            #. name (None, string): The file name.
               If None is given, name will be split from relativePath.
            #. description (False, string, pickable object): Any random description about the file.
               If False is given, the description info won't be updated, 
               otherwise it will be update to what description argument value is.
            #. klass (False, class): The dumped object class. If False is given, 
               the class info won't be updated, otherwise it will be update to what klass argument value is.
            #. dump (False, string): The new dump method. If False is given, the old one will be used.
            #. pull (False, string): The new pull method. If False is given, the old one will be used.
            #. ACID (boolean): Whether to ensure the ACID (Atomicity, Consistency, Isolation, Durability) 
               properties of the repository upon dumping a file. This is ensured by dumping the file in
               a temporary path first and then moving it to the desired path.
               If None is given, repository ACID property will be used.
            #. verbose (boolean): Whether to be warn and informed about any abnormalities.
        """
        # check ACID
        if ACID is None:
            ACID = self.__ACID
        assert isinstance(ACID, bool), "ACID must be boolean"
        # get relative path normalized
        relativePath = os.path.normpath(relativePath)
        if relativePath == '.':
            relativePath = ''
            assert name != '.pyrepinfo', "'.pyrepinfo' is not allowed as file name in main repository directory"
            assert name != '.pyrepstate', "'.pyrepstate' is not allowed as file name in main repository directory"
            assert name != '.pyreplock', "'.pyreplock' is not allowed as file name in main repository directory"
        if name is None:
            assert len(relativePath), "name must be given when relative path is given as empty string or as a simple dot '.'"
            relativePath,name = os.path.split(relativePath)
        # get file info dict
        fileInfoDict, errorMessage = self.get_file_info(relativePath, name)
        assert fileInfoDict is not None, errorMessage
        # get real path
        realPath = os.path.join(self.__path, relativePath)
        # check if file exists
        if verbose:
            if not os.path.isfile( os.path.join(realPath, name) ):
                warnings.warn("file '%s' is in repository but does not exist in the system. It is therefore being recreated."%os.path.join(realPath, name))
        # convert dump and pull methods to strings
        if not dump:
            dump = fileInfoDict["dump"]
        if not pull:
            pull = fileInfoDict["pull"]
        # get savePath
        if ACID:
            savePath = os.path.join(tempfile.gettempdir(), name)
        else:
            savePath = os.path.join(realPath,name)
        # dump file
        try:
            exec( dump.replace("$FILE_PATH", savePath.encode('string-escape')) ) 
        except Exception as e:
            message = "unable to dump the file (%s)"%e
            if 'pickle.dump(' in dump:
                message += '\nmore info: %s'%str(get_pickling_errors(value))
            raise Exception( message )
        # copy if ACID
        if ACID:
            try:
                shutil.copyfile(savePath, os.path.join(realPath,name))
            except Exception as e:
                os.remove(savePath)
                if verbose:
                    warnings.warn(e)
                return
            os.remove(savePath)
        # update timestamp
        fileInfoDict["timestamp"] = datetime.utcnow()
        if description is not False:
            fileInfoDict["description"] = description
        if klass is not False:
            assert inspect.isclass(klass), "klass must be a class definition"
            fileInfoDict["class"] = klass
        # save repository
        self.save()
    
    def update(self, *args, **kwargs):
        """Alias to update_file"""
        self.update_file(*args, **kwargs)
        
    def pull_file(self, relativePath, name=None, pull=None, update=True):
        """
        Pull a file's data from the Repository.
        
        :Parameters:
            #. relativePath (string): The relative to the repository path of the directory where the file should be pulled.
            #. name (string): The file name.
               If None is given, name will be split from relativePath.
            #. pull (None, string): The pulling method. 
               If None, the pull method saved in the file info will be used.
               If a string is given, the string should include all the necessary imports, 
               a '$FILE_PATH' that replaces the absolute file path when the dumping will be performed
               and finally a PULLED_DATA variable.
               e.g "import numpy as np; PULLED_DATA=np.loadtxt(fname='$FILE_PATH')"  
            #. update (boolean): If pull is not None, Whether to update the pull method stored in the file info by the given pull method.
        
        :Returns:
            #. data (object): The pulled data from the file.
        """
        # get relative path normalized
        relativePath = os.path.normpath(relativePath)
        if relativePath == '.':
            relativePath = ''
            assert name != '.pyrepinfo', "pulling '.pyrepinfo' from main repository directory is not allowed."
            assert name != '.pyrepstate', "pulling '.pyrepstate' from main repository directory is not allowed."
            assert name != '.pyreplock', "pulling '.pyreplock' from main repository directory is not allowed."
        if name is None:
            assert len(relativePath), "name must be given when relative path is given as empty string or as a simple dot '.'"
            relativePath,name = os.path.split(relativePath)
        # get file info
        fileInfo, errorMessage = self.get_file_info(relativePath, name)
        assert fileInfo is not None, errorMessage
        # get absolute path
        realPath = os.path.join(self.__path, relativePath)
        assert os.path.exists(realPath), "relative path '%s'within repository '%s' does not exist"%(relativePath, self.__path)
        # file path
        fileAbsPath = os.path.join(realPath, name)
        assert os.path.isfile(fileAbsPath), "file '%s' does not exist in absolute path '%s'"%(name,realPath)
        if pull is None:
            pull = fileInfo["pull"]
        # try to pull file
        DH = Repository.__DICT_HIDE
        Repository.__DICT_HIDE = False
        try:
            exec( pull.replace("$FILE_PATH", os.path.join(realPath,name).encode('string-escape')) )
        except Exception as e:
            m = pull.replace("$FILE_PATH", os.path.join(realPath,name).encode('string-escape')) 
            Repository.__DICT_HIDE = DH
            raise Exception( "unable to pull data using '%s' from file (%s)"%(m,e) )
        finally:
            Repository.__DICT_HIDE = DH
        # update
        if update:
            fileInfo["pull"] = pull
        # return data
        return PULLED_DATA
            
    def pull(self, *args, **kwargs):
        """Alias to pull_file"""
        return self.pull_file(*args, **kwargs)    
    

    
    
    