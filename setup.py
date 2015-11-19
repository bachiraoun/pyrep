try:
    from setuptools import setup
except:
    from distutils.core import setup

setup(
  name = 'pyrep',
  packages = ['pyrep'], # this must be the same as the name above
  version = '1.0',
  description = 'This is a pythonic way to organize dumping and pulling python objects and/or any other type of files to a repository.',
  author = 'Bachir Aoun',
  author_email = 'bachir.aoun@e-aoun.com',
  url = 'https://github.com/bachiraoun/pyrep',
  download_url = 'https://github.com/bachiraoun/pyrep/tree/v1.0',
  keywords = ['repository', 'data management'], 
  classifiers = [],
)
