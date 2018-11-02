# standard distribution imports
import os, sys
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
from pprint import pprint
import copy, json
try:
    import cPickle as pickle
except:
    import pickle

# import pylocker
from pylocker import Locker

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
else:
    str        = str
    unicode    = unicode
    bytes      = str
    long       = long
    basestring = basestring

# set warnings filter to always
warnings.simplefilter('always')



DEFAULT_DUMP="""
try:
    import cPickle as pickle
except:
    import pickle
fd = open('$FILE_PATH', 'wb')
pickle.dump( value, fd, protocol=2 )
fd.close()
"""

DEFAULT_PULL="""
import os
try:
    import cPickle as pickle
except:
    import pickle
fd = open(os.path.join( '$FILE_PATH' ), 'rb')
PULLED_DATA = pickle.load( fd )
fd.close()
"""

def path_required(func):
    """Decorate methods when repository path is required."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.path is None:
            warnings.warn('Must load or initialize the repository first !')
            return
        return func(self, *args, **kwargs)
    return wrapper


class Repository(object):
    """
    This is a pythonic way to organize dumping and pulling python objects
    or any type of files to a folder or directory that we call repository.
    Any directory can be a repository, it suffices to initialize a Repository
    instance in a directory to start dumping and pulling object into it.
    Any directory that has .pyreprepo binary file in it is theoretically a
    pyrep Repository.

    :Parameters:
        #. repo (None, path, Repository): This is used to initialize a Repository instance.\n
           If None, Repository is initialized but not assigned to any directory.\n
           If Path, Repository is loaded from directory path unless directory is not a repository and error will be raised.\n
           If Repository, current instance will cast the given Repository instance.
    """
    def __init__(self, path=None):
        #L =  Locker(filePath=None, lockPass=str(uuid.uuid1()), lockPath=os.path.join(repoPath, self.__repoLock))
        #acquired, code = L.acquire_lock()
        self.__repoLock  = '.pyreplock'
        self.__repoFile  = '.pyreprepo'
        self.__dirInfo   = '.pyrepdirinfo'
        self.__dirLock   = '.pyrepdirlock'
        self.__fileInfo  = '.%s_pyrepfileinfo'  # %s replaces file name
        self.__fileLock  = '.%s_pyrepfilelock'  # %s replaces file name
        self.__objectDir = '.%s_pyrepobjectdir' # %s replaces file name
        # initialize repository
        self.reset()
        # if path is not None, load existing repository
        if path is not None:
            assert self.is_repository(path), "given path is not a repository. use create_repository or give a valid repository path"
            self.load_repository(repo)

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
                        rp = os.path.join(repoPath, relPath, dn)
                        rsd = {dn:[]}
                        relSynchedList.append(rsd)
                        _walk_dir(relPath=rp, relDirList=k[dn], relSynchedList=rsd[dn])
                        if not len(rsd[dn]):
                            _ = relSynchedList.pop( relSynchedList.index(rsd) )
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

    def __save_dirinfo(self, info, dirInfoPath, create=False):
        # create main directory info file
        oldInfo = None
        if info is None and os.path.isfile(dirInfoPath):
            with open(dirInfoPath, 'r') as fd:
                oldInfo = json.load(fd)
            if self.__repo['repository_unique_name'] != oldInfo['repository_unique_name']:
                info = ''
        if info is None and create:
            info = ''
        if info is not None:
            if os.path.isfile(dirInfoPath):
                if oldInfo is None:
                    with open(dirInfoPath, 'r') as fd:
                        oldInfo = json.load(fd)
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
                    'info':info}
            with open(dirInfoPath, 'w') as fd:
                json.dump( info,fd )

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
                #print(removeDirs)
                #print(removeFiles)
        # return result and errors list
        return len(errors)==0, errors

    def __set_repository_directory(self, relativePath, dirList):
        splitted = self.to_repo_relative_path(path=relativePath, split=True)
        if splitted == ['']:
            self.__repo['walk_repo'] = dirList
            return True, ""
        error = None
        cDir  = self.__repo['walk_repo']
        for idx, dirname in enumerate(splitted):
            dList = [d for d in cDir if isinstance(d, dict)]
            if not len(dList):
                cDir = None
                error = "Repository relative directory '%s' not found"%os.sep.join(splitted[:idx])
                break
            cDict = [d for d in dList if dirname in d]
            if not len(cDict):
                cDir = None
                error = "Repository relative directory '%s' not found"%os.sep.join(splitted[:idx])
                break
            if idx == len(splitted)-1:
                cDict[0][dirname] = dirList
            else:
                cDir = cDict[0][dirname]
        # return
        return False, error

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






    @property
    def path(self):
        """The repository instance path which points to the directory where
        .pyreprepo is."""
        return self.__path

    @property
    def uniqueName(self):
        """Get repository unique name"""
        return self.__repo['repository_unique_name']

    def reset(self):
        #self.__locker = Locker(filePath=None, lockPass=str(uuid.uuid1()),lockPath='.pyreplock')
        self.__path   = None
        self.__repo   = {'repository_unique_name': str(uuid.uuid1()),
                         'create_utctime': time.time(),
                         'last_update_utctime': None,
                         'pyrep_version': str(__version__),
                         'repository_description': '',
                         'walk_repo': []}


    def is_repository(self, path):
        """
        Check if there is a Repository in path.

        :Parameters:
            #. path (string): The real path of the directory where to check if there is a repository.

        :Returns:
            #. result (boolean): Whether its a repository or not.
        """
        if path.strip() in ('','.'):
            path = os.getcwd()
        repoPath = os.path.realpath( os.path.expanduser(path) )
        return os.path.isfile( os.path.join(repoPath,self.__repoFile) )

    def load_repository(self, path, verbose=True):
        """
        Load repository from a directory path and update the current instance.

        :Parameters:
            #. path (string): The path of the directory from where to load the repository.
               If '.' or an empty string is passed, the current working directory will be used.
            #. verbose (boolean): Whether to be verbose about abnormalities

        :Returns:
             #. repository (pyrep.Repository): returns self repository with loaded data.
        """
        # try to open
        if path.strip() in ('','.'):
            path = os.getcwd()
        repoPath = os.path.realpath( os.path.expanduser(path) )
        if not self.is_repository(repoPath):
            raise Exception("No repository found in '%s'"%str(repoPath))
        # get pyreprepo path
        repoInfoPath = os.path.join(repoPath, self.__repoFile)
        try:
            fd = open(repoInfoPath, 'rb')
        except Exception as e:
            raise Exception("Unable to open repository file(%s)"%e)
        # before doing anything try to lock repository
        # always create new locker, this makes the repository thread safe
        L =  Locker(filePath=None, lockPass=str(uuid.uuid1()), lockPath=os.path.join(repoPath, self.__repoLock))
        acquired, code = L.acquire_lock()
        # check if acquired.
        if not acquired:
            warnings.warn("code %s. Unable to aquire the lock when calling 'load_repository'. You may try again!"%(code,) )
            return
        try:
            # unpickle file
            try:
                #repo = pickle.load( fd )
                repo = json.load( fd )
            except Exception as err:
                fd.close()
                raise Exception("Unable to load json repository (%s)"%str(err))
            finally:
                fd.close()
            # check if it's a pyreprepo instance
            assert isinstance(repo, dict), "pyrep repo must be a dictionary"
            assert "create_utctime" in repo, "'create_utctime' must be a key in pyrep repo dict"
            assert "last_update_utctime" in repo, "'last_update_utctime' must be a key in pyrep repo dict"
            assert "pyrep_version" in repo, "'pyrep_version' must be a key in pyrep repo dict"
            assert "walk_repo" in repo, "'walk_repo' must be a key in pyrep repo dict"
            assert isinstance(repo['walk_repo'], list), "pyrep info 'walk_repo' key value must be a list"
            # get paths dict
            repoFiles, errors = self.__sync_files(repoPath=repoPath, dirs=repo['walk_repo'])
            if len(errors) and verbose:
                warnings.warn("\n".join(errors))
                #print("\n".join(errors))
            self.reset()
            self.__path = repoPath
            self.__repo['repository_unique_name'] = repo['repository_unique_name']
            self.__repo['repository_description'] = repo['repository_description']
            self.__repo['create_utctime']         = repo['create_utctime']
            self.__repo['last_update_utctime']    = repo['last_update_utctime']
            self.__repo['walk_repo']              = repoFiles
        except Exception as e:
            L.release_lock()
            raise Exception(e)
        finally:
            L.release_lock()
        # return
        return self

    def create_repository(self, path, description=None, info=None, replace=True):
        """
        create a repository in a directory.
        This method insures the creation of the directory in the system if it is missing.\n

        **N.B. This method erases existing pyrep repository in the path but not the repository files.**

        :Parameters:
            #. path (string): The real absolute path where to create the Repository.
               If '.' or an empty string is passed, the current working directory will be used.
            #. description (None, str): Repository description.
            #. info (None, str): Repository main directory information.
            #. replace (boolean): Whether to replace existing repository.

        :Returns:
            #. success (boolean): Whether creating repository was successful
            #. message (None, str): Any returned message.
        """
        assert isinstance(replace, bool), "replace must be boolean"
        assert isinstance(path, str), "path must be string"
        if info is None:
            info = ''
        assert isinstance(info, str), "info must be None or a string"
        if description is None:
            description = ''
        assert isinstance(description, str), "description must be None or a string"
        # get real path
        if path.strip() in ('','.'):
            path = os.getcwd()
        realPath = os.path.realpath( os.path.expanduser(path) )
        # reset if replace is set to True
        message = None
        if self.is_repository(realPath):
            if not replace:
                message = "A pyrep Repository already exists in the given path '%s' set replace to True if you need to proceed."%path
                return False, message
            else:
                message = "Old existing pyrep repository existing in the given path '%s' has been replaced."%path
                try:
                    for _df in os.listdir(realPath):
                        _p = os.path.join(realPath, _df)
                        if os.path.isdir(_p):
                            shutil.rmtree( _p )
                        else:
                            os.remove(_p)
                except Exception as err:
                    message = "Unable to clean remove repository before create (%s)"%(str(err))
                    return False, message
        if not os.path.isdir(realPath):
            os.makedirs(realPath)
        elif len(os.listdir(realPath)):
            return False, "Not allowed to create repository in a non empty directory"
        # reset repository
        oldRepo = self.__repo
        self.reset()
        self.__path = realPath
        self.__repo['repository_description'] = description
        # save repository
        saved = self.save(info=info)
        if not saved:
            self.__repo = oldRepo
            message = "Absolute path and directories might be created but no pyrep Repository is created."
            return False, message
        # return
        return True, message


    @path_required
    def save(self, info=None):
        """ Save repository '.pyreprepo' to disk and create (if missing) or
         update (if info is not None) '.pyrepdirinfo'.

        :Parameters:
            #. info (None, str): Repository main directory information. If given
               will be replaced.

        :Returns:
            # success (bool): Whether saving was successful.
            # error (None, string): Fail to save repository message in case
              saving is not successful. If success is True, error will be None.
        """
        # get info
        if info is not None:
            assert isinstance(info, str), "info must be None or a string"
        dirInfoPath = os.path.join(self.__path, self.__dirInfo)
        if info is None and not os.path.isfile(dirInfoPath):
            info = ''
        # create and acquire lock
        L =  Locker(filePath=None, lockPass=str(uuid.uuid1()), lockPath=os.path.join(self.__path, self.__repoLock))
        acquired, code = L.acquire_lock()
        # check if acquired.
        if not acquired:
            return False, "code %s. Unable to aquire the lock when calling 'save'. You may try again!"%(code,)
        # open file
        repoInfoPath = os.path.join(self.__path, self.__repoFile)
        try:
            self.__save_dirinfo(info=info, dirInfoPath=dirInfoPath)
            # create repository
            with open(repoInfoPath, 'w') as fd:
                self.__repo["last_update_utctime"] = time.time()
                json.dump( self.__repo,fd )
        except Exception as err:
            L.release_lock()
            return False, "Unable to save repository (%s)"%err
        finally:
            L.release_lock()
            return True, None

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
        assert isinstance(path, str), "given path must be a string"
        name = os.path.basename(path)
        if not len(name):
            return False, "empty name is not allowed"
        # exact match
        for em in [self.__repoLock,self.__repoFile,self.__dirInfo,self.__dirLock]:
            if name == em:
                return False, "name '%s' is reserved for pyrep internal usage"%em
        # pattern match
        for pm in [self.__fileInfo,self.__fileLock,self.__objectDir]:
            if name == pm or (name.endswith(pm[3:]) and name.startswith('.')):
                return False, "name pattern '%s' is not allowed as result may be reserved for pyrep internal usage"%pm
        # name is ok
        return True, None

    def to_repo_relative_path(self, path, split=False):
        """
        Given an absolute path, return relative path to diretory

        :Parameters:
            #. path (str): Path as a string
            #. split (boolean): Whether to split path to its components

        :Returns:
            #. relativePath (str, list): Relative path as a string or as a list
               of components if split is True
        """
        path  = os.path.normpath(path)
        if path == '.':
            path = ''
        path = path.split(self.__path)[-1]
        if split:
            return path.split(os.sep)
        else:
            return path

    @path_required
    def get_repository_state(self, relaPath=None):
        """
        Get a list representation of repository state along with useful
        information. List state is ordered in levels


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
            for fname in sorted([f for f in dirList if isinstance(f, str)]):
                _rp = os.path.join(self.__path,relaPath,fname)
                if os.path.isdir(_rp) and df.startswith('.') and df.endswith(self.__objectDir[3:]):
                    fileDict = {'type':'objectdir',
                                'exists':True,
                                'pyrepfileinfo':os.path.isfile(os.path.join(self.__path,relaPath,self.__fileInfo%df)),
                               }

                else:
                    fileDict = {'type':'file',
                                'exists':os.path.isfile(_rp),
                                'pyrepfileinfo':os.path.isfile(os.path.join(self.__path,relaPath,self.__fileInfo%df)),
                               }
                state.append({_rp:fileDict})
            # loop directories
            for ddict in sorted([d for d in dirList if isinstance(d, dict)]):
                dirname = list(ddict)[0]
                _walk_dir(relaPath=os.path.join(relaPath,dirname), dirList=ddict[dirname])
        # call recursive _walk_dir
        if relaPath is None:
            _walk_dir(relaPath='', dirList=self.__repo['walk_repo'])
        else:
            assert isinstance(relaPath, str), "relaPath must be None or a str"
            relaPath = self.to_repo_relative_path(path=relaPath, split=False)
            spath    = relaPath.split(os.sep)
            dirList=self.__repo['walk_repo']
            while len(spath):
                dirname = spath.pop(0)
                dList = [d for d in dirList if isinstance(d, dict)]
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
        Get repository directory list.

        :Parameters:
            #. relativePath (string): The relative to the repository path .

        :Returns:
            #. dirList (None, list): List of directories and files in repository
               directory. If directory is not tracked in repository None is
               returned
        """
        return copy.deepcopy(self.__get_repository_directory(relativePath))

    def is_repository_directory(self, relativePath):
        """
        Get whether directory is registered in repository.

        :Parameters:
            #. relativePath (string): The relative to the repository path.

        :Returns:
            #. result (boolean): Whether directory is tracked and registered.
        """
        return self.__get_repository_directory(relativePath) is not None

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
    #    L =  Locker(filePath=None, lockPass=str(uuid.uuid1()), lockPath=os.path.join(realPath, self.__dirLock))
    #    acquired, code = L.acquire_lock()
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
    #        L.release_lock()
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
    def add_directory(self, relativePath, info=None, clean=False):
        """
        Add a directory in the repository and creates its
        attribute in the Repository with utc timestamp.
        It insures adding all the missing directories in the path.

        :Parameters:
            #. relativePath (string): The relative to the repository path of the
               directory to add in the repository.
            #. info (None, string): Any random info about the added directory.
            #. clean (boolean): Whether to remove existing non repository
               tracked files and folders in all created directory chain tree.

        :Returns:
            #. success (boolean): Whether adding the directory was successful.
            #. reason (None, string): Reason why directory was not added.
        """
        assert isinstance(relativePath, str), "relativePath must be a string"
        if info is not None:
            assert isinstance(info, str), "info must be None or a string"
        # normalise path
        path = self.to_repo_relative_path(path=relativePath, split=False)
        # whether to replace
        if self.is_repository_directory(path):
            return False, "Directory is already tracked in repository"
        # check whether name is allowed
        allowed, reason = self.is_name_allowed(path)
        if not allowed:
            return False, reason
        # create directories
        error   = None
        posList = self.__repo['walk_repo']
        dirPath = self.__path
        spath   = path.split(os.sep)
        for idx, name in enumerate(spath):
            # create and acquire lock.
            L =  Locker(filePath=None, lockPass=str(uuid.uuid1()), lockPath=os.path.join(dirPath, self.__dirLock))
            acquired, code = L.acquire_lock()
            if not acquired:
                error = "Code %s. Unable to aquire the lock when adding '%s'. All prior directories were added. You may try again, to finish adding directory"%(code,dirPath)
                break
            # add to directory
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
                self.__save_dirinfo(info=[None, info][idx==len(spath)-1],
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
            finally:
                L.release_lock()
            if error is not None:
                break
        # save
        if error is None:
            _, error = self.save()
        # return
        return error is None, error

    def get_repository_parent_directory(self, relativePath):
        """
        """
        return copy.deepcopy(self.__get_repository_parent_directory(relativePath))


    @path_required
    def remove_directory(self, relativePath, clean=False):
        """
        Remove directory from repository tracking.

        :Parameters:
            #. relativePath (string): The relative to the repository path of the
               directory to remove from the repository.
            #. clean (boolean): Whether to os remove directory. If False only
               tracked files will be removed along with left empty directories.

        :Returns:
            #. success (boolean): Whether removing the directory was successful.
            #. reason (None, string): Reason why directory was not removed.
        """
        assert isinstance(clean, bool), "clean must be boolean"
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
            return False, "Repository relative directory '%s' seems to be missing. call maintain_repository to fix all issues"
        # get and acquire lock
        L =  Locker(filePath=None, lockPass=str(uuid.uuid1()), lockPath=os.path.join(self.__path,parentPath,self.__dirLock))
        acquired, code = L.acquire_lock()
        if not acquired:
            error = "Code %s. Unable to aquire the lock when adding '%s'. All prior directories were added. You may try again, to finish adding directory"%(code,realPath)
            return False, error
        error = None
        try:
            dirList = self.__get_repository_parent_directory(relativePath=relativePath)
            assert dirList is not None, "Given relative path '%s' is not a repository directory"%(relativePath,)
            stateBefore = self.get_repository_state(relaPath=parentPath)
            _files = [f for f in dirList if isinstance(f, str)]
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
        finally:
            L.release_lock()
        # return
        return error is None, error


    @path_required
    def rename_directory(self, relativePath, newName):
        """
        Rename a directory in the repository. It insures renaming the directory in the system.

        :Parameters:
            #. relativePath (string): The relative to the repository path of
               the directory to be renamed.
            #. newName (string): The new directory name.

        :Returns:
            #. success (boolean): Whether renaming the directory was successful.
            #. reason (None, string): Reason why directory was not renamed.
        """
        relativePath = self.to_repo_relative_path(path=relativePath, split=False)
        parentPath, dirName = os.path.split(relativePath)
        if relativePath == '':
            return False, "Renaming main repository directory is not allowed"
        realPath = os.path.join(self.__path,relativePath)
        newRealPath = os.path.join(os.path.dirname(realPath), newName)
        if os.path.isdir(newRealPath):
            return False, "New directory path '%s' already exist"%(newRealPath,)
        # get directory parent list
        L =  Locker(filePath=None, lockPass=str(uuid.uuid1()), lockPath=os.path.join(self.__path,parentPath, self.__dirLock))
        acquired, code = L.acquire_lock()
        if not acquired:
            error = "Code %s. Unable to aquire the lock when adding '%s'. All prior directories were added. You may try again, to finish adding directory"%(code,dirPath)
            return False, error
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
            self.__save_dirinfo(info=None, dirInfoPath=parentPath, create=False)
        except Exception as err:
            error = str(err)
        finally:
            L.release_lock()
        if error is not None:
            _, error = self.save()
        # return
        return error is None, error

#
