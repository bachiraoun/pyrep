"""
This script will work from within the main package directory.

python setup.py sdist bdist_wheel
twine upload dist/pyrep-...
"""
from setuptools import setup
from setuptools.command.build_py import build_py
import os


class BuildPyWithoutScripts(build_py):
    """
    Builds the package without the project's own helper scripts.
    """

    def find_package_modules(self, package, packageDir):
        """
        Lists the package modules and leaves out setup.py.

        :Parameters:
            #. package (str): The package name.
            #. packageDir (str): The directory of the package.

        :Returns:
            #. modules (list): Tuples of package, module name and file path.
        """
        modules = build_py.find_package_modules(self, package, packageDir)
        return [item for item in modules if item[1] != 'setup']


# set package path and name
PACKAGE_PATH = '.'
PACKAGE_NAME = 'pyrep'

# automatically create MANIFEST.in
commands = [# include MANIFEST.in
            '# include this file, to ensure we can recreate source distributions',
            'include MANIFEST.in',
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
Programming Language :: Python
Programming Language :: Python :: 3
Programming Language :: Python :: 3 :: Only
Programming Language :: Python :: 3.9
Programming Language :: Python :: 3.10
Programming Language :: Python :: 3.11
Programming Language :: Python :: 3.12
Programming Language :: Python :: 3.13
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
                    "A Repository can be created in any directory or folder, it suffices to initialize a Repository instance in a directory to start dumping and pulling object into it.",
                    "Any directory or a folder that contains a .pyreprepo binary file in it, is theoretically a pyrep Repository.",
                    "By default dump and pull methods use pickle to serialize storing python objects.",
                    "Practically any other methods can be used simply by providing the means and the required libraries in a simple form of string.",]
DESCRIPTION      = [ LONG_DESCRIPTION[0] ]

## get package info
PACKAGE_INFO={}
infoPath = '__pkginfo__.py'
with open(infoPath) as fd:
    exec(fd.read(), PACKAGE_INFO)

# create meta data
metadata = dict(name             = PACKAGE_NAME,
                packages         = [PACKAGE_NAME],
                package_dir      = {PACKAGE_NAME: '.'},
                version          = PACKAGE_INFO['__version__'] ,
                author           = "Bachir AOUN",
                author_email     = "bachir.aoun@e-aoun.com",
                description      = "\n".join(DESCRIPTION),
                long_description = "\n".join(LONG_DESCRIPTION),
                url              = "https://bachiraoun.github.io/pyrep/",
                download_url     = "https://github.com/bachiraoun/pyrep",
                license          = 'AGPL-3.0-only',
                python_requires  = ">=3.9",
                install_requires = ["pylocker>=5.0.0,<6",],
                classifiers      = [_f for _f in CLASSIFIERS.split('\n') if _f],
                platforms        = ["Windows", "Linux", "Mac OS-X", "Unix"] )

# setup
setup(cmdclass={'build_py': BuildPyWithoutScripts}, **metadata)
