"""
PYthon REPository or pyrep package provides a pythonic way to organize dumping and pulling
python objects and other type of files to a folder or a directory that is called
repository. A Repository can be created in any directory or folder, it suffices to
initialize a Repository instance in a directory to start dumping and pulling objects into
it. Any directory or a folder that contains a .pyreprepo binary file in it, is
theoretically a pyrep Repository. By default dump and pull methods use pickle to
serialize storing python objects. Practically any other method can be used simply by
providing the means and the required libraries in a simple form of string.


Installation guide:
===================
pyrep is a pure python module for Python 3.9 or newer that only needs pylocker. Fork pyrep's
`github repository <https://github.com/bachiraoun/pyrep/>`_, copy the package to python's
site-packages, and do the same with pylocker's
`github repository <https://github.com/bachiraoun/pylocker/>`_.


Package Functions:
==================
"""
from .__pkginfo__ import __version__, __author__, __email__, __onlinedoc__, __repository__
from .Repository import Repository


def get_version():
    """
    Gets pyrep's version number.

    :Returns:
        #. version (str): The version number.
    """
    return __version__

def get_author():
    """
    Gets pyrep's author's name.

    :Returns:
        #. author (str): The name of the author.
    """
    return __author__

def get_email():
    """
    Gets pyrep's author's email.

    :Returns:
        #. email (str): The email of the author.
    """
    return __email__

def get_doc():
    """
    Gets pyrep's official online documentation link.

    :Returns:
        #. link (str): The URL of the documentation.
    """
    return __onlinedoc__

def get_repository():
    """
    Gets pyrep's official online repository link.

    :Returns:
        #. link (str): The URL of the source repository.
    """
    return __repository__
