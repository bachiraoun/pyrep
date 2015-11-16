import os
from setuptools import setup

PATH =  os.path.dirname(os.path.realpath(__file__))
setup(
    # Application name
    name="pyrep",
    # Packages
    packages=["pyrep"],
    # packages dir
    package_dir={'pyrep': '.'},
    # Version number
    version="0.1.0",
    # Application author details
    author="Bachir AOUN",
    author_email="bachir.aoun@e-aoun.com",
    # Include additional files into the package
    include_package_data=True,
    # Details
    url="https://github.com/bachiraoun/pyrep",
    # license file
    license="LICENSE.txt",
    # short description
    description='This is a pythonic way to organize dumping and pulling python objects and/or any other type of files to a repository.',
    # long description
    long_description=open( "README.md" ).read(),
    # Dependent packages (distributions)
    #install_requires=['numpy',],
    #setup_requires=['numpy'], 
)