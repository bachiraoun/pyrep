# standard distribution imports
import os
import sys
import uuid
try:
    import cPickle as pickle
except:
    import pickle

# pyrep imports
from pyrep import __version__
    

        
class PyrepInfo(dict):
    def __init__(self):
        self.__reset_version()
        self.__reset_id()
        self.__path = None
        # set directories and files dictionaries
        dict.__setitem__(self, "directories", {})
        dict.__setitem__(self, "files",       {})
        
    def __setitem__(self, key, value):
        raise Exception("setting item is not allowed")
    
    def __getitem__(self, key):
        raise Exception("getting item is not allowed")
    
    def keys(self, *args, **kwargs):
        raise Exception("getting keys list is not allowed")

    def values(self, *args, **kwargs):
        raise Exception("getting values list is not allowed")
    
    def items(self, *args, **kwargs):
        raise Exception("getting items list is not allowed")
        
    def __reset_id(self):
        dict.__setitem__(self, "__uuid__", str(uuid.uuid1()))
    
    def __reset_version(self):
        dict.__setitem__(self, "__version__", __version__)
    
    def _update_path(self, path):
        self.__path = path
        
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
        
    def add_directory(self, relativePath):
        """Ensures adding directory in the given relative path"""
        path = os.path.normpath(relativePath)
        # create directories
        currentDir  = self.path
        currentDict = dict.__getitem__(self,"directories")
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
            
    def get_directory(self, relativePath):
        currentDir  = self.path
        dirInfoDict = dict.__getitem__(self, "directories")
        for dir in os.path.normpath(relativePath).split(os.sep):
            currentDir = os.path.join(currentDir, dir)
            assert os.path.exists(currentDir), "directory '%s' is not found"%currentDir
            assert dirInfoDict.get(dir, None) is not None, "directory '%s' is not registered in PyrepInfo"%currentDir   
            dirInfoDict = dirInfoDict[dir]["directories"]
        return dirInfoDict
            
    def add_file(self, relativePath, file, info={}):
        # ensure directory added
        self.add_directory(relativePath)
        # get directory info dict
        dirInfoDict = self.get_directory(relativePath)
        print dirDict
            
            
            
    
class Repository(object):
    def __init__(self, path=None):
        if path is not None:
            if self.is_repository(path):
                self.__info = self.get_repository_info(path)
            else:
                self.__info = self.initialize_repository(path)
        else:
            self.__info = None
        
  
    def is_repository(self, path):
        if not os.path.isdir(path):
            return False
        if ".pyrepinfo" not in os.listdir(path):
            return False
        
    def initialize_repository(self, path):
        self.__info = PyrepInfo()
        self.save(path)
     
    def get_repository_info(self, path): 
        # try to open
        infoPath = os.path.join(path, ".pyrepinfo")
        try:
            fd = open(infoPath, 'rb')
        except Exception as e:
            raise Exception("unable to open repository (%s)"%e)   
        # unpickle file
        try:
            info = pickle.load( fd )
        except Exception as e:
            fd.close()
            raise Exception("unable to open repository (%s)"%e)  
        finally:
            fd.close()
        # check if its a PyrepInfo instance
        if not isinstance(info, PyrepInfo): 
            raise Exception("No repository found in %s"%s)  
        else:
            # update info path
            info._update_path(path)
            return info
            
    def dump_repository_info(self, path):
        """
        Save repository info.
        
        :Parameters:
            #. path (string): the file path to save the engine
        """
        if self.__info is None:
            raise Exception("must initialize repository first!")
        # open file
        infoPath = os.path.join(path, ".pyrepinfo")
        try:
            fd = open(infoPath, 'wb')
        except Exception as e:
            raise Exception("unable to open repository info for saving (%s)"%e)   
        # save engine
        oldPath = info._update_path(path)
        try:
            pickle.dump( self.__info, fd, protocol=pickle.HIGHEST_PROTOCOL )
        except Exception as e:
            fd.close()
            raise Exception( LOGGER.error("Unable to save repository info (%s)"%e) )
        finally:
            fd.close()
    
    
    