# standard distribution imports
import os
import uuid
import warnings
import tarfile
try:
    import cPickle as pickle
except:
    import pickle

# pyrep imports
from pyrep import __version__
    
        
class Repository(dict):
    """
    This is a pythonic way to organize dumping and pulling python objects 
    or any type of file to a repository.
    Any folder can be a repository, it suffice to initialize a repository instance 
    in a folder to start dumping and pulling object into in.
    A Repository folder, is any folder that has .pyrepinfo file in it.
    """
    def __init__(self, repo=None):
        self.__path = None
        self.__lock = True
        self.__reset_repository()
        self.__cast(repo)
     
    def __str__(self):
        if self.__path is None:
            return ""
        string = os.path.normpath(self.__path)+"\n"
        # walk files
        leftAdjust = "  "
        for file in dict.__getitem__(self, 'files').keys():
            string += leftAdjust
            string += file+'\n'
        # walk folders
        for folder in sorted(list(self.walk_folders())):
            # split folder path
            splitPath = folder.split(os.sep)
            # get left space
            leftAdjust = ''.join(['  '*(len(item)>0) for item in splitPath])
            # get folder info
            dirInfoDict, errorMessage = self.get_directory_info(folder)
            assert dirInfoDict is not None, errorMessage
            # append folders to representation
            string += leftAdjust
            string += os.sep+str(splitPath[-1])+'\n'
            # append files to representation
            leftAdjust += "  "
            for file in dict.__getitem__(dirInfoDict, 'files').keys():
                string += leftAdjust
                string += file+"\n"
        return string    
    
    def __repr__(self):
        repr = self.__class__.__name__+" (Version "+str(self.version)+")"
        if self.__path is None:
            return repr
        repr += '\n'
        repr += self.__path+":"+str(dict.__getitem__(self, 'files').keys())
        # walk folders
        for folder in sorted(list(self.walk_folders())):
            folderRepr = os.path.normpath(folder)
            # get folder info
            dirInfoDict, errorMessage = self.get_directory_info(folder)
            assert dirInfoDict is not None, errorMessage
            folderRepr += ":"+str( dict.__getitem__(dirInfoDict, 'files').keys() )
            repr += " ; "           
            repr += folderRepr
        return str(repr)
        
    #def __setitem__(self, key, value):
    #    if self.lock:
    #        raise Exception("setting item is not allowed")
    #    dict.__setitem__(self, key, value)
    #    
    #def __getitem__(self, key):
    #    if self.lock:
    #        raise Exception("getting item is not allowed")
    #    dict.__getitem__(self, key)
    #    
    #def keys(self, *args, **kwargs):
    #    if self.lock:
    #        raise Exception("getting keys list is not allowed")
    #    return dict.keys(self)
    #    
    #def values(self, *args, **kwargs):
    #    if self.lock:
    #        raise Exception("getting values list is not allowed")
    #    return dict.values(self)
    #    
    #def items(self, *args, **kwargs):
    #    if self.lock:
    #        raise Exception("getting items list is not allowed")
    #    return dict.items(self)
    
    def __cast(self, repo):
        if repo is None:
            return
        if isinstance(repo, Repository):
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
            
    def __update_repository(self, repository=None):
        if repository is None:
            self.__reset_repository()
        else:
            self.update(repository)
        
    @property
    def lock(self):
        """Get the lock value."""
        return self.__lock
        
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
    
    def walk_folders(self):
        """Walk the repository and yield all found folders relative path"""
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
        Initialize a repository in a folder
        
        :Parameters:
            #. path (str): The path of the folder where to create a repository.
            #. replace (boolean): Whether to replace any existing repository.
            #. save (boolean): Whether to save the repository .pyrepinfo file upon initializing.
        """
        if path.strip() in ('','.'):
            path = os.getcwd()
        path = os.path.expanduser(path)
        normPath = os.path.normpath(path)
        if not replace:
            assert not self.is_repository(normPath), "A repository already exist in this path. Force re-initialization using by setting replace flag to True"
        self.__update_repository(repository=None)
        # set path
        self.__path = normPath
        # save repository
        if save:
            self.save()
    
    def load(self, path):
        """
        Load repository from a folder and update the current instance.
        
        :Parameters:
            #. path (str): The path of the folder from where to load the repository.
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
            self.__lock = False
            info = pickle.load( fd )
        except Exception as e:
            fd.close()
            self.__lock = True
            raise Exception("unable to pickle load repository (%s)"%e)  
        finally:
            fd.close()
            self.__lock = False
        # check if its a PyrepInfo instance
        if not isinstance(info, Repository): 
            raise Exception("No repository found in %s"%s)  
        else:
            # update info path
            self.__update_repository(info)
            self.__path = repoPath
    
    def save(self):
        """ Save repository .pyrepinfo to disk. """
        if self.__path is None:
            raise Exception('Must load or initialize the repository first !')
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
    
    def create_package(self, path=None, name=None, mode=None):
        """
        Create a tar file package of all the repository files and folders. 
        Only files and folders that are stored in the repository info 
        are stored in the package tar file.
        
        :Parameters:
            #. path (None, str): The real absolute path where to create the package.
               If None, it will be created in the same folder as the repository
               If '.' or an empty string is passed, the current working directory will be used.
            #. name (None, str): The name to give to the package file
               If None, the package folder name will be used with the appropriate extension added.
            #. mode (None, str): The writing mode of the tarfile.
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
        assert os.path.isdir(root), 'absolute path %s is not a valid folder'%path
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
        # walk folder and create empty folders
        for folder in sorted(list(self.walk_folders())):
            t = tarfile.TarInfo( folder )
            t.type = tarfile.DIRTYPE
            tarHandler.addfile(t)
        # walk files and add to tar
        for file in self.walk_files():
            tarHandler.add(os.path.join(self.__path,file), arcname=file)
        # save repository .pyrepinfo
        tarHandler.add(".pyrepinfo", arcname=".pyrepinfo")
        # close tar file
        tarHandler.close()
        
    def remove_repository(self, relatedFiles=False, relatedFolders=False):
        """
        Remove .pyrepinfo file from path if exists. 
        
        :Parameters:
            #. path (str): The path of the folder where to remove an existing repository.
            #. relatedFiles (boolean): Whether to also remove all related files from system as well.
            #. relatedFolders (boolean): Whether to also remove all related folders from system as well.
               Folders will be removed only if they are left empty after removing the files.
        """
        if self.__path is None:
            return
        # check for security  
        if rootPath == os.path.realpath('/..') :
            warnings.warn('you are about to wipe out your system !!! action aboarded')
            return
        if not self.is_repository(self.__path):
            return
        # delete files
        if relatedFiles:
            for relativePath in self.walk_files():
                os.remove( os.path.join(self.__path, relativePath) )
        # delete folders
        if relatedFolders:
            for relativePath in reversed(list(self.walk_folders())):
                realPath = os.path.join(self.__path, relativePath)
                # protect from wiping out the system
                if not len(os.listdir(realPath)):
                    os.rmdir( realPath )
        # delete repository       
        os.remove( os.path.join(self.__path,".pyrepinfo") )              
            
    def is_repository(self, path):
        """
        Check if its a repository. 
        
        :Parameters:
            #. path (str): The path of the folder where to check if there is a repository.
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
            #. relativePath (str): The relative to the repository path of the directory to add in the repository.
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
                currentDict[dir] = {"directories":{}, "files":{}}
            currentDict = currentDict[dir]["directories"]
            currentDir  = dirPath
            
    def get_directory_info(self, relativePath): 
        """
        get directory info in the repository
        
        :Parameters:
            #. relativePath (str): The relative to the repository path of the directory.
        """
        relativePath = os.path.normpath(relativePath)
        # if root folder
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
            #. relativePath (str): The relative to the repository path of the directory where the file is.
            #. name (str): The file name.
        """
        errorMessage = ""
        relativePath = os.path.normpath(relativePath)
        dirInfoDict, errorMessage = self.get_directory_info(relativePath)
        assert dirInfoDict is not None, errorMessage
        fileInfo = dict.__getitem__(dirInfoDict, "files").get(name, None)
        if fileInfo is None:
            errorMessage = "file %s does not exist in relative path %s"%(name, relativePath)
        return fileInfo, errorMessage
           
    def dump_file(self, file, relativePath, name, dump=None, pull=None, replace=False, save=True):
        """
        Dump a file to the repository.
        
        :Parameters:
            #. file (object): The file to add. It is any python object.
            #. relativePath (str): The relative to the repository path of the directory where the file should be dumped.
            #. name (str): The file name.
            #. dump (none, str): The dumping method. 
               If None it will be set automatically to pickle and therefore the object must be pickleable.
               If a string is given, the string should include all the necessary imports 
               and a '$FILE_PATH' that replaces the absolute file path when the dumping will be performed.
               e.g. "import numpy as np; np.savetxt(fname='$FILE_PATH', X=file, fmt='%.6e')"
            #. pull (none, str): The pulling method. 
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
            assert name != '.pyrepinfo', "'.pyrepinfo' is not allowed as file name in main repository folder"
        # ensure directory added
        self.add_directory(relativePath)
        normPath = os.path.join(self.__path, relativePath)
        # get directory info dict
        dirInfoDict, errorMessage = self.get_directory_info(relativePath)
        assert dirInfoDict is not None, errorMessage
        if dict.__getitem__(dirInfoDict, "files").has_key(name):
            assert replace, "a file with the name '%s' is already defined in repository dictionary info. Set replace flag to True if you want to replace the existing file"%(name)
        # convert dump and pull methods to strings
        if dump is None:
            dump="pickle.dump( file, open('$FILE_PATH', 'wb'), protocol=pickle.HIGHEST_PROTOCOL )"
        if pull is None:
            pull="PULLED_DATA = pickle.load( open(os.path.join( '$FILE_PATH' ), 'rb') )"
        # try to dump the file
        try:
            exec( dump.replace("$FILE_PATH", os.path.join(normPath,name).encode('string-escape')) ) 
        except Exception as e:
            raise Exception( "unable to dump the file (%s)"%e )
        # save the new file to the repository
        dict.__getitem__(dirInfoDict, "files")[name] = {"dump":dump,"pull":pull}
        # save repository
        if save:
            self.save()
    
    def pull_file(self, relativePath, name, pull=None, update=True):
        """
        Pull a file from the repository.
        
        :Parameters:
            #. relativePath (str): The relative to the repository path of the directory where the file should be pulled.
            #. name (str): The file name.
            #. pull (none, str): The pulling method. 
               If None, the pull method saved in the file info will be used.
               If a string is given, the string should include all the necessary imports, 
               a '$FILE_PATH' that replaces the absolute file path when the dumping will be performed
               and finally a PULLED_DATA variable.
               e.g "import numpy as np; PULLED_DATA=np.loadtxt(fname='$FILE_PATH')"  
            #. update (boolean): If pull is not None, Whether to update the pull method stored in the file info by the given pull method.
        """
        relativePath = os.path.normpath(relativePath)
        if relativePath == '.':
            relativePath = ''
            assert name != '.pyrepinfo', "pulling '.pyrepinfo' from main repository folder is not allowed."
        # get file info
        fileInfo, errorMessage = self.get_file_info(relativePath, name)
        assert fileInfo is not None, errorMessage
        # get absolute path
        normPath = os.path.join(self.__path, relativePath)
        assert os.path.exists(normPath), "relative path '%s'within repository '%s' does not exist"%(relativePath, self.__path)
        # file path
        fileAbsPath = os.path.join(normPath, name)
        assert os.path.isfile(fileAbsPath), "file '%s' does not exist in absolute path '%s'"%(name,normPath)
        if pull is None:
            pull = fileInfo["pull"]
        # try to pull file
        try:
            exec( pull.replace("$FILE_PATH", os.path.join(normPath,name).encode('string-escape')) )
        except Exception as e:
            raise Exception( "unable to pull data from file (%s)"%e )
        # update
        if update:
            fileInfo["pull"] = pull
        # return data
        return PULLED_DATA
            
            
    

    
    
    