# standard distribution imports
import os
import uuid
import warnings
import tarfile
import datetime
try:
    import cPickle as pickle
except:
    import pickle

# pyrep imports
from pyrep import __version__
    
#### Define decorators ###
def path_required(func):
    def wrapper(self, *args, **kwargs):
        if self.path is None:
            warnings.warn('Must load or initialize the repository first !')
            return
        return func(self, *args, **kwargs)
    return wrapper

def unlock_required(func):
    def wrapper(self, *args, **kwargs):
        if self.LOCK:
            warnings.warn("Repository class '%s' method '%s' is locked!"%(self.__class__.__name__,func.__name__))
            return
        return func(self, *args, **kwargs)
    return wrapper

           
class Repository(dict):
    """
    This is a pythonic way to organize dumping and pulling python objects 
    or any type of files to a repository. Any directory can be a repository, 
    it suffices to initialize a Repository instance in a directory to start 
    dumping and pulling object into it. Any directory that has .pyrepinfo 
    binary file in it is theoretically a pyrep Repository.
    
    :Parameters:
        #. repo (None, path, Repository): This is used to initialize a Repository instance.
           If None, Repository is initialized but not assigned to any directory.
           If Path, Repository is loaded from directory path unless directory is not a repository and error will be raised.
           If Repository, current instance will cast the given Repository instance.
    """
    __LOCK = True 
    def __init__(self, repo=None):
        self.__path = None
        self.__reset_repository()
        self.__cast(repo)
        self.__LOCK = True
    
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
        for directory in sorted(list(self.walk_directories())):
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
        
    @unlock_required
    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
    
    @unlock_required
    def __getitem__(self, key):
        dict.__getitem__(self, key)
     
    @unlock_required
    def keys(self, *args, **kwargs):
        """Keys is a locked method and modified to be a private method only callable from within the instance."""
        return dict.keys(self)
    
    @unlock_required
    def values(self, *args, **kwargs):
        """values is a locked method and modified to be a private method only callable from within the instance."""
        return dict.values(self)
        
    @unlock_required
    def items(self, *args, **kwargs):
        """items is a locked method and modified to be a private method only callable from within the instance."""
        return dict.items(self)
    
    @unlock_required
    def pop(self, *args, **kwargs):
        """pop is a locked method and modified to be a private method only callable from within the instance."""
        return dict.pop(self, *args, **kwargs)
    
    @unlock_required
    def update(self, *args, **kwargs):
        """update is a locked method and modified to be a private method only callable from within the instance."""
        return dict.pop(self, *args, **kwargs)
    
    @unlock_required
    def popitem(self, *args, **kwargs):
        """popitem is a locked method and modified to be a private method only callable from within the instance."""
        return dict.popitem(self, *args, **kwargs)
    
    @unlock_required
    def viewkeys(self, *args, **kwargs):
        """viewkeys is a locked method and modified to be a private method only callable from within the instance."""
        return dict.viewkeys(self, *args, **kwargs)
    
    @unlock_required
    def viewvalues(self, *args, **kwargs):
        """viewvalues is a locked method and modified to be a private method only callable from within the instance."""
        return viewvalues.viewkeys(self, *args, **kwargs)  
    
    def __cast(self, repo):
        if repo is None:
            return
        if isinstance(repo, Repository):
            self.__reset_repository()
            self.__update_repository(repo)
        elif isinstance(repo, basestring):
            repo = str(repo)
            if self.is_repository(repo):
                self.load(repo)
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
    
    @property
    def LOCK(self):
        """Get the lock value."""
        return self.__LOCK 
            
    @property
    def path(self):
        """Get the path of this repository."""
        return self.__path
    
    @property
    def version(self):
        """Get the version of this repository."""
        return dict.__getitem__(self,"__version__")
        
    @property
    def id(self):
        """Get the universally unique id of this repository."""
        return dict.__getitem__(self,"__uuid__")
        
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
        for directory in sorted(list(self.walk_directories())):
            directoryRepr = os.path.normpath(directory)
            # get directory info
            dirInfoDict, errorMessage = self.get_directory_info(directory)
            assert dirInfoDict is not None, errorMessage
            directoryRepr += ":["+','.join( dict.__getitem__(dirInfoDict, 'files').keys())+']'
            repr.append(directoryRepr)
        return repr
        
    def walk_files(self):
        """Walk the repository and yield all found files relative path"""
        def walk_repository_files(directory, relativePath):
            directories = dict.__getitem__(directory, 'directories')
            files       = dict.__getitem__(directory, 'files')
            for f in files:
                yield os.path.join(relativePath, f)
            for k,d in dict.items(directories):
                path = os.path.join(relativePath, k)
                for e in walk_repository_files(d, path):
                    yield e
        return walk_repository_files(self, relativePath="")
    
    def walk_directories(self):
        """Walk the repository and yield all found directories relative path"""
        def walk_repository_files(directory, relativePath):
            directories = dict.__getitem__(directory, 'directories')
            dirNames = dict.keys(directories)
            for d in dirNames:
                yield os.path.join(relativePath, d)
            for k,d in dict.items(directories):
                path = os.path.join(relativePath, k)
                for e in walk_repository_files(d, path):
                    yield e
        return walk_repository_files(self, relativePath="")
        
    def initialize(self, path, replace=False, save=True): 
        """
        Initialize a repository in a directory
        
        :Parameters:
            #. path (string): The path of the directory where to create a repository.
            #. replace (boolean): Whether to replace any existing repository.
            #. save (boolean): Whether to save the repository .pyrepinfo file upon initializing.
        """
        if path.strip() in ('','.'):
            path = os.getcwd()
        realPath = os.path.realpath( os.path.expanduser(path) )
        if not replace:
            assert not self.is_repository(realPath), "A repository already exist in this path. Force re-initialization using by setting replace flag to True"
        self.__reset_repository()
        # set path
        self.__path = realPath
        # save repository
        if save:
            self.save()
    
    def load(self, path):
        """
        Load repository from a directory and update the current instance.
        
        :Parameters:
            #. path (string): The path of the directory from where to load the repository.
        """
        # try to open
        repoPath = os.path.realpath( os.path.expanduser(path) )
        if not self.is_repository(repoPath):
            raise Exception("no repository found in '%s'"%str(repoPath))
        repoInfoPath = os.path.join(repoPath, ".pyrepinfo")
        try:
            fd = open(repoInfoPath, 'rb')
        except Exception as e:
            raise Exception("unable to open repository file(%s)"%e)   
        # unpickle file
        try:
            Repository.__LOCK = False
            repo = pickle.load( fd )
        except Exception as e:
            fd.close()
            Repository.__LOCK = True
            raise Exception("unable to pickle load repository (%s)"%e)  
        finally:
            fd.close()
            Repository.__LOCK = False
        # check if its a PyrepInfo instance
        if not isinstance(repo, Repository): 
            raise Exception("No repository found in %s"%s)  
        else:
            # update info path
            self.__reset_repository()
            self.__update_repository(repo)
            self.__path = repoPath
    
    @path_required
    def save(self):
        """ Save repository .pyrepinfo to disk. """
        # open file
        repoInfoPath = os.path.join(self.__path, ".pyrepinfo")
        try:
            fd = open(repoInfoPath, 'wb')
        except Exception as e:
            raise Exception("unable to open repository info for saving (%s)"%e)   
        # save repository
        try:
            pickle.dump( self, fd, protocol=pickle.HIGHEST_PROTOCOL )
        except Exception as e:
            fd.close()
            raise Exception( LOGGER.error("Unable to save repository info (%s)"%e) )
        finally:
            fd.close()
    
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
        for directory in sorted(list(self.walk_directories())):
            t = tarfile.TarInfo( directory )
            t.type = tarfile.DIRTYPE
            tarHandler.addfile(t)
        # walk files and add to tar
        for file in self.walk_files():
            tarHandler.add(os.path.join(self.__path,file), arcname=file)
        # save repository .pyrepinfo
        tarHandler.add(".pyrepinfo", arcname=".pyrepinfo")
        # close tar file
        tarHandler.close()
        
    def create_repository(self, path, checkout=True):
        """
        Create a repository at given absolute path.
        This method insures the creation of the directory in the system.
        
        **N.B. On some systems and some paths, creating a directory may requires root permissions.**  
        
        :Parameters:
            #. path (None, string): The real absolute path where to create the package.
               If None, it will be created in the same directory as the repository
               If '.' or an empty string is passed, the current working directory will be used.
            #. checkout (boolean): Whether to checkout the current Repository instance to the newly created one
        """
        realPath = os.path.realpath( os.path.expanduser(path) )
        assert not self.is_repository(realPath), "A pyrep Repository already exists in the given path '%s'"%path
        # create directory
        if not os.path.isdir(realPath):
            os.makedirs(realPath)
        # create Repository
        repo = Repository()
        repo.initialize(path=realPath, replace=True, save=True)
        # checkout
        if checkout:
            self.__update_repository(repo)
    
    def remove_repository(self, path=None, relatedFiles=False, relatedFolders=False):
        """
        Remove .pyrepinfo file from path if exists and related files and directories if wanted. 
        
        :Parameters:
            #. path (None, string): The path of the directory where to remove an existing repository.
               If None, current repository is removed if initialized
            #. relatedFiles (boolean): Whether to also remove all related files from system as well.
            #. relatedFolders (boolean): Whether to also remove all related directories from system as well.
               Directories will be removed only if they are left empty after removing the files.
        """
        if path is not None:
            realPath = os.path.realpath( os.path.expanduser(path) )
        else:
            realPath = self.__path
        if realPath is None:
            warnings.warn('path is None and current Repository is not initialized!')
            return
        if not self.is_repository(realPath):
            warnings.warn("No repository found in '%s'!"%realPath)
            return
        # check for security  
        if realPath == os.path.realpath('/..') :
            warnings.warn('You are about to wipe out your system !!! action aboarded')
            return
        # get repo
        if path is not None:
            repo = Repository()
            repo.load(realPath)
        else:
            repo = self
        # delete files
        if relatedFiles:
            for relativePath in repo.walk_files():
                os.remove( os.path.join(repo.path, relativePath) )
        # delete directories
        if relatedFolders:
            for relativePath in reversed(list(repo.walk_directories())):
                realPath = os.path.join(repo.path, relativePath)
                # protect from wiping out the system
                if not len(os.listdir(realPath)):
                    os.rmdir( realPath )
        # delete repository       
        os.remove( os.path.join(repo.path,".pyrepinfo") )  
        # reset repository
        repo.__reset_repository()             
            
    def is_repository(self, path):
        """
        Check if its a repository. 
        
        :Parameters:
            #. path (string): The path of the directory where to check if there is a repository.
        
        :Returns:
            #. result (boolean): Whether its a repository or not.
        """
        realPath = os.path.realpath( os.path.expanduser(path) )
        if not os.path.isdir(realPath):
            return False
        if ".pyrepinfo" not in os.listdir(realPath):
            return False
        return True
    
    def add_directory(self, relativePath):
        """
        Adds a directory in the repository. 
        It insures adding all the missing directories in the path.
        
        :Parameters:
            #. relativePath (string): The relative to the repository path of the directory to add in the repository.
        """
        path = os.path.normpath(relativePath)
        # create directories
        currentDir  = self.path
        currentDict = dict.__getitem__(self,"directories")
        if path in ("","."):
            return currentDict
        for dir in path.split(os.sep):
            dirPath = os.path.join(currentDir, dir)
            # create directory
            if not os.path.exists(dirPath):
                 os.mkdir(dirPath)
            # create dictionary key
            if currentDict.get(dir, None) is None:    
                currentDict[dir] = {"directories":{}, "files":{}, "timestamp":datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            currentDict = currentDict[dir]["directories"]
            currentDir  = dirPath
            
    def get_directory_info(self, relativePath): 
        """
        get directory info in the repository
        
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
    
    def get_file_info(self, relativePath, name): 
        """
        get file info in the repository
        
        :Parameters:
            #. relativePath (string): The relative to the repository path of the directory where the file is.
            #. name (string): The file name.
        
        :Returns:
            #. info (None, dictionary): The file information dictionary.
               If None, it means an error has occurred.
            #. error (string): The error message if any error occurred.
        """
        errorMessage = ""
        relativePath = os.path.normpath(relativePath)
        dirInfoDict, errorMessage = self.get_directory_info(relativePath)
        assert dirInfoDict is not None, errorMessage
        fileInfo = dict.__getitem__(dirInfoDict, "files").get(name, None)
        if fileInfo is None:
            errorMessage = "file %s does not exist in relative path %s"%(name, relativePath)
        return fileInfo, errorMessage
           
    def dump_file(self, value, relativePath, name, dump=None, pull=None, replace=False, save=True):
        """
        Dump a file to the repository using its value.
        
        :Parameters:
            #. value (object): The value of a file to dump and add to the repository. It is any python object or file.
            #. relativePath (str): The relative to the repository path of the directory where the file should be dumped.
            #. name (string): The file name.
            #. dump (None, string): The dumping method. 
               If None it will be set automatically to pickle and therefore the object must be pickleable.
               If a string is given, the string should include all the necessary imports 
               and a '$FILE_PATH' that replaces the absolute file path when the dumping will be performed.
               e.g. "import numpy as np; np.savetxt(fname='$FILE_PATH', X=value, fmt='%.6e')"
            #. pull (None, string): The pulling method. 
               If None it will be set automatically to pickle and therefore the object must be pickleable.
               If a string is given, the string should include all the necessary imports, 
               a '$FILE_PATH' that replaces the absolute file path when the dumping will be performed
               and finally a PULLED_DATA variable.
               e.g "import numpy as np; PULLED_DATA=np.loadtxt(fname='$FILE_PATH')"  
            #. replace (boolean): Whether to replace any existing file with the same name if existing.
            #. save (boolean): Whether to save repository .pyrepinfo to disk.
        """
        relativePath = os.path.normpath(relativePath)
        if relativePath == '.':
            relativePath = ''
            assert name != '.pyrepinfo', "'.pyrepinfo' is not allowed as file name in main repository directory"
        # ensure directory added
        self.add_directory(relativePath)
        # ger real path
        realPath = os.path.join(self.__path, relativePath)
        # get directory info dict
        dirInfoDict, errorMessage = self.get_directory_info(relativePath)
        assert dirInfoDict is not None, errorMessage
        if dict.__getitem__(dirInfoDict, "files").has_key(name):
            assert replace, "a file with the name '%s' is already defined in repository dictionary info. Set replace flag to True if you want to replace the existing file"%(name)
        # convert dump and pull methods to strings
        if dump is None:
            dump="pickle.dump( value, open('$FILE_PATH', 'wb'), protocol=pickle.HIGHEST_PROTOCOL )"
        if pull is None:
            pull="PULLED_DATA = pickle.load( open(os.path.join( '$FILE_PATH' ), 'rb') )"
        # try to dump the file
        try:
            exec( dump.replace("$FILE_PATH", os.path.join(realPath,name).encode('string-escape')) ) 
        except Exception as e:
            raise Exception( "unable to dump the file (%s)"%e )
        # save the new file to the repository
        dict.__getitem__(dirInfoDict, "files")[name] = {"dump":dump,"pull":pull,"timestamp":datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        # save repository
        if save:
            self.save()
    
    def update_file(self, value, relativePath, name, save=True):
        """
        Update the a value of a file that is already in the repository.
        
        :Parameters:
            #. value (object): The value of the file to update. It is any python object or a file.
            #. relativePath (str): The relative to the repository path of the directory where the file should be dumped.
            #. name (string): The file name.
            #. save (boolean): Whether to save repository .pyrepinfo to disk.
        """
        # get relative path normalized
        relativePath = os.path.normpath(relativePath)
        if relativePath == '.':
            relativePath = ''
            assert name != '.pyrepinfo', "'.pyrepinfo' is not allowed as file name in main repository directory"
        # get file info dict
        fileInfoDict, errorMessage = self.get_file_info(relativePath, name)
        assert fileInfoDict is not None, errorMessage
        # get real path
        realPath = os.path.join(self.__path, relativePath)
        # convert dump and pull methods to strings
        dump = fileInfoDict["dump"]
        pull = fileInfoDict["pull"]
        # try to dump the file
        try:
            exec( dump.replace("$FILE_PATH", os.path.join(realPath,name).encode('string-escape')) ) 
        except Exception as e:
            raise Exception( "unable to dump the file (%s)"%e )
        # update timestamp
        fileInfoDict["timestamp"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # save repository
        if save:
            self.save()
                
    def pull_file(self, relativePath, name, pull=None, update=True):
        """
        Pull a file from the repository.
        
        :Parameters:
            #. relativePath (string): The relative to the repository path of the directory where the file should be pulled.
            #. name (string): The file name.
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
        relativePath = os.path.normpath(relativePath)
        if relativePath == '.':
            relativePath = ''
            assert name != '.pyrepinfo', "pulling '.pyrepinfo' from main repository directory is not allowed."
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
        try:
            exec( pull.replace("$FILE_PATH", os.path.join(realPath,name).encode('string-escape')) )
        except Exception as e:
            raise Exception( "unable to pull data from file (%s)"%e )
        # update
        if update:
            fileInfo["pull"] = pull
        # return data
        return PULLED_DATA
            
        
    

    
    
    