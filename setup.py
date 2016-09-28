"""
This script will work from within the main package directory.
"""
try:
    from setuptools import setup
except:
    from distutils.core import setup
from distutils.util import convert_path
import os, sys

# set package path and name
PACKAGE_PATH = '.'
PACKAGE_NAME = 'pyrep'

# check python version
if sys.version_info[:2] < (2, 6):
    raise RuntimeError("Python version 2.6, 2.7 or >= 3.2 required.")

# automatically create MANIFEST.in
commands = [# include MANIFEST.in
            '# include this file, to ensure we can recreate source distributions',
            'include MANIFEST.in'
            # exclude all .log files
            '\n# exclude all logs',
            'global-exclude *.log',
            # exclude all other non necessary files 
            '\n# exclude all other non necessary files ',
            'global-exclude .project',
            'global-exclude .pydevproject',
            # exclude all of the subversion metadata
            '\n# exclude all of the subversion metadata',
            'global-exclude *.svn*',
            'global-exclude .svn/*',
            'global-exclude *.git*',
            'global-exclude .git/*',
            # include all LICENCE files
            '\n# include all license files found',
            'global-include ./*LICENSE.*',
            # include all README files
            '\n# include all readme files found',
            'global-include ./*README.*',
            'global-include ./*readme.*']         
with open('MANIFEST.in','w') as fd:
    for l in commands:
        fd.write(l)
        fd.write('\n')


# declare classifiers
CLASSIFIERS = """\
Development Status :: 4 - Beta
Intended Audience :: Science/Research
Intended Audience :: Developers
License :: OSI Approved :: GNU Affero General Public License v3
Programming Language :: Python
Programming Language :: Python :: 2
Programming Language :: Python :: 2.6
Programming Language :: Python :: 2.7
Topic :: Software Development
Topic :: Software Development :: Build Tools
Topic :: Scientific/Engineering
Operating System :: Microsoft :: Windows
Operating System :: POSIX
Operating System :: Unix
Operating System :: MacOS
"""

# create descriptions                    
LONG_DESCRIPTION = ["This package provides a pythonic way to organize dumping and pulling python objects and other type of files to a folder or a directory that is called repository.",
                    "A Repository can be created in any directory or folder, it suffices to initialize a Repository instance in a directory to start dumping and pulling object into it. .",
                    "Any directory or a folder that contains a .pyrepinfo binary file in it, is theoretically a pyrep Repository."
                    "By default dump and pull methods use pickle to serialize storing python objects.",
                    "Practically any other methods can be used simply by providing the means and the required libraries in a simple form of string.",]
DESCRIPTION      = [ LONG_DESCRIPTION[0] ]


# get package info
PACKAGE_INFO={}
ver_path = convert_path('__init__.py')
with open(ver_path) as ver_file:
    exec(ver_file.read(), PACKAGE_INFO)


# create meta data
metadata = dict(name             = PACKAGE_NAME,
                packages         = [PACKAGE_NAME],
                package_dir      = {PACKAGE_NAME: '.'},
                version          = PACKAGE_INFO['__version__'] ,
                author           = "Bachir AOUN",
                author_email     = "bachir.aoun@e-aoun.com",
                description      = "\n".join(DESCRIPTION),
                long_description = "\n".join(LONG_DESCRIPTION),
                url              = "http://bachiraoun.github.io/pyrep/",
                download_url     = "https://github.com/bachiraoun/pyrep",
                license          = 'GNU',
                install_requires = ["pylocker",],
                classifiers      = [_f for _f in CLASSIFIERS.split('\n') if _f],
                platforms        = ["Windows", "Linux", "Mac OS-X", "Unix"], )
                
# setup              
setup(**metadata)


