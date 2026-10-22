# pyrep
This package provides a pythonic way to organize dumping and pulling python objects and other type of files to a Repository. A Repository can be created in any directory or folder. Repository directories are transferable between operating systems. By default dump and pull methods use pickle to serialize storing python objects. Practically any other methods can be used simply by providing the means and the required libraries in a simple form of string.

Repositories are safe to use from several threads and processes at the same time. Access is coordinated by [pylocker](https://pypi.org/project/pylocker/), and the repository index, the info files and the data files are all written to a temporary file first and renamed into place, so a crash leaves the previous content complete. Loading a repository removes the temporary files and the orphan files that crashed operations left behind, when they are older than an hour, unless `removeTemporaryFiles=False` or `removeOrphanFiles=False` is given. Operations that need several steps, such as renaming a directory, write a journal first, and the next process to take the lock completes what a crash interrupted.

## Installation
Fork or download the [github repository](https://github.com/bachiraoun/pyrep/) and copy the `pyrep` package to python's site-packages. Then install its one dependency:
```
pip install pylocker
```
pyrep needs Python 3.9 or newer. The tests are run on Python 3.10 to 3.13.

## Testing
```
python3 tests/run_tests.py            ## everything, one line for each test
python3 tests/run_tests.py --quiet    ## only the summary
python3 tests/run_tests.py --quick    ## skip the slow crash tests
python3 tests/run_tests.py --list     ## the test files
python3 benchmark/bench_contention.py --processes 100 --threads 10   ## contention benchmark
python3 benchmark/bench_ladder.py --markdown results.md                ## ladder from 1 to 500 processes x 10 threads, tables for the docs
```
The suite includes 10 processes with several threads each fighting over the same files, and crash tests that kill a writer in the middle of a write.

## Example

```python
from pyrep import Repository

# create repository, an existing one is only replaced when replace=True is given
REP = Repository()
REP.create_repository('~/test_repository')

# add some directories
REP.add_directory("folder1/folder2/folder3")
REP.add_directory("folder1/archive1/archive2/archive3/archive3")

# dump some python objects, missing directories are created
REP.dump("This is a string data to pickle and store in the repository", 'pickle_text_test1')
REP.dump("another text", "folder1/folder2/folder3/pickle_text_test2")

# dump using any code that defines dump(path, value) and pull(path)
dump = "import numpy as np; dump = lambda path, value: np.savetxt(fname=path, X=value, fmt='%.6e')"
pull = "import numpy as np; pull = lambda path: np.loadtxt(fname=path)"
REP.dump(np.random.random((3, 1)), 'folder1/archive1/archive2/numpy_test', dump=dump, pull=pull)

# pull data back
print(REP.pull("folder1/folder2/folder3/pickle_text_test2"))
>>> another text
print(REP.pull('folder1/archive1/archive2/numpy_test'))
>>> [0.13943792 0.04656474 0.56458421]

# update, copy, rename and remove
REP.update("an updated text", 'pickle_text_test1')
REP.copy_file('pickle_text_test1', 'folder1/copy_of_text')
REP.rename_file('folder1/copy_of_text', 'folder1/renamed_text')
REP.remove_file('folder1/renamed_text')
```

An instance keeps the list of files it loaded or saved last. Pulling or asking about a file that another instance or process added reloads the list by itself, and it costs nothing for names the instance already knows. Listings and files that others removed only change after `REP.refresh_repository()`.

## Online Documentation
https://bachiraoun.github.io/pyrep/

## Author
Bachir Aoun
