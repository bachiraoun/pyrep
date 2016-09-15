"""
PYthon REPository or pyrep package provides a pythonic way to organize dumping and pulling 
python objects and other type of files to a folder or a directory that is called 
repository. A Repository can be created in any directory or folder, it suffices to 
initialize a Repository instance in a directory to start dumping and pulling objects into 
it. Any directory or a folder that contains a .pyrepinfo binary file in it, is 
theoretically a pyrep Repository. By default dump and pull methods use pickle to 
serialize storing python objects. Practically any other method can be used simply by 
providing the means and the required libraries in a simple form of string.


Installation guide:
===================
pyrep is a pure python 2.7.x module that needs no particular installation. One can either 
fork pyrep's `github repository <https://github.com/bachiraoun/pyrep/>`_ and copy the 
package to python's site-packages or use pip as the following:


.. code-block:: console
    
    
        pip install pyrep
        

Package Functions:
==================
"""
from __pkginfo__ import __version__, __author__, __email__, __onlinedoc__, __repository__, __pypi__
from Repository import Repository


def get_version():
    """Get pyrep's version number."""
    return __version__ 

def get_author():
    """Get pyrep's author's name."""
    return __author__     
 
def get_email():
    """Get pyrep's author's email."""
    return __email__   
    
def get_doc():
    """Get pyrep's official online documentation link."""
    return __onlinedoc__       
    
def get_repository():
    """Get pyrep's official online repository link."""
    return __repository__        
    
def get_pypi():
    """Get pyrep pypi's link."""
    return __pypi__   
    
    
    