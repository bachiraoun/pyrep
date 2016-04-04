# pyrep
This package provides a pythonic way to organize dumping and pulling python objects and other type of files to a Repository. A Repository can be created in any directory or folder. Repository directories are transferable between operating systems. By default dump and pull methods use pickle to serialize storing python objects. Practically any other methods can be used simply by providing the means and the required libraries in a simple form of string.  

## Installation
pyrep needs no especial installations and requires merely an installation of python.

## Testing
It is so far tested with python2.7 installed on all of windows 7, fedora 18.0 and mac yosemite 10.10 machines.

## Example

```
from pyrep.Repository import Repository
import numpy as np

# create repository
REP = Repository()
REP.create_repository('~/test_repository')

# add some directories
REP.add_directory("folder1/folder2/folder3")
REP.add_directory("folder1/archive1/archive2/archive3/archive3")
REP.add_directory("directory1/directory2")

# dump some text files
value = "This is a string data to pickle and store in the repository"
REP.dump(value, relativePath='.', name='pickle_text_test1')
REP.dump("another text", relativePath="folder1/folder2/folder3", name='pickle_text_test2')

# dump using numpy
dump="import numpy as np; np.savetxt(fname='$FILE_PATH', X=value, fmt='%.6e')"
pull="import numpy as np; PULLED_DATA=np.loadtxt(fname='$FILE_PATH')"
value = np.random.random((3,1))
REP.dump(value, relativePath='folder1/archive1/archive2', name='numpy_test', dump=dump, pull=pull)

# lets pull some data
print REP.pull(relativePath="folder1/folder2/folder3", name='pickle_text_test2')
>>> another text
print REP.pull(relativePath='folder1/archive1/archive2', name='numpy_test')
>>> array([[ 0.13943792],
           [ 0.04656474],
           [ 0.56458421]])
```

## Online Documentation
http://bachiraoun.github.io/pyrep/

## Author
Bachir Aoun





