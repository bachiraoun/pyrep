# pyrep

**PYthon REPository**: store Python objects and files in a plain folder, organized like a file system, and read them back by name. Several threads and processes can use the same folder safely.

## What is pyrep?
pyrep turns an ordinary folder into a small, safe store for your Python data. Instead of inventing file names and writing your own load and save code, you give each object a path such as `results/run1/positions`, then `dump` it and `pull` it back. Folders inside the repository work like normal folders: you can add, copy, rename and remove them.

It suits scientific and engineering work: many runs or workers saving results, checkpoints and intermediate data into one place, without any server or database.

Pickle is the default format. Any other format works too: give pyrep a short piece of code that dumps and pulls the data.

## Why use it?
* **Simple:** `dump`, `pull`, `update`, `copy_file`, `rename_file` and `remove_file`, plus the same for directories.
* **Any format:** pickle by default, or your own dump and pull code (NumPy text files, JSON, images, and so on).
* **Shared safely:** threads and processes lock the repository through [pylocker](https://github.com/bachiraoun/pylocker/). The benchmarks run up to 128 processes, each with many threads and up to 1024 threads in total, on one repository, and check that nothing is lost or corrupted.
* **Crash safe:** index, info files and data files are written to a temporary file and then renamed, so a crash leaves the previous content complete. Operations that need several steps, such as renaming a directory, write a journal first, and the next process to take the lock completes what a crash interrupted.
* **Self-cleaning:** loading a repository removes the temporary files and the orphan files that crashed operations left behind, when they are older than an hour. Turn this off with `removeTemporaryFiles=False` or `removeOrphanFiles=False`.
* **Portable and transparent:** a repository is a folder of files that can be moved between operating systems, and `create_package()` packs it into a tar file next to it.

## Limitations
* **Not a database:** there are no queries, no search by content and no transactions that span several files.
* **Whole objects:** `pull` reads a whole file and `dump` writes a whole file. There is no partial read or write.
* **Pickle trust:** pickle can run code when loaded. Only open repositories you trust. Custom dump and pull code is a string that pyrep runs as given, so the same applies.
* **Listings can lag:** `walk_files_path` and the other `walk_*` methods show the list the instance last loaded. Looking up a file by name (`pull`, `is_repository_file`) notices changes made by other instances or processes and reloads the list by itself. Call `refresh_repository()` when you need a fresh listing without such a lookup.
* **Needs pylocker:** locking depends on it.
* **Python only:** the default pickle files are readable by Python only. pyrep needs Python 3.9 or newer.

## Installation
pyrep is pure Python and needs Python 3.9 or newer. The tests are run on Python 3.10 to 3.13. Fork or download the [github repository](https://github.com/bachiraoun/pyrep/) and copy the `pyrep` package to your python's site-packages. Do the same with [pylocker](https://github.com/bachiraoun/pylocker/), its one dependency.

## Quick start
```python
from pyrep import Repository

## create a repository, an existing one is only replaced when replace=True is given
rep = Repository()
rep.create_repository('~/my_repository')

## dump objects, missing directories are created
rep.dump("some text", 'notes/first')

## pull the object back
print(rep.pull('notes/first'))
>>> some text

## update, copy, rename and remove
rep.update("new text", 'notes/first')
rep.copy_file('notes/first', 'notes/second')
rep.rename_file('notes/second', 'notes/renamed')
rep.remove_file('notes/renamed')
```

### Directories
```python
rep.add_directory("project/runs/run1")
for filePath in rep.walk_files_path("project", recursive=True):
    print(filePath)
```

### Custom formats
```python
import numpy as np

## code that defines dump(path, value) and pull(path)
dump = "import numpy as np; dump = lambda path, value: np.savetxt(fname=path, X=value, fmt='%.6e')"
pull = "import numpy as np; pull = lambda path: np.loadtxt(fname=path)"
rep.dump(np.random.random((3, 1)), 'project/runs/run1/matrix', dump=dump, pull=pull)
print(rep.pull('project/runs/run1/matrix'))
```

### Several processes
```python
## any thread or process can load the same folder
rep = Repository('~/my_repository')
```
An instance keeps the list of files it loaded or saved last. Pulling a file, or asking whether one exists, reloads the list by itself when another instance or process changed it. Plain listings (`walk_files_path` and so on) only reload on such a lookup or after `rep.refresh_repository()`.

## Testing
```bash
python3 tests/run_tests.py            ## everything, one line for each test
python3 tests/run_tests.py --quiet    ## only the summary
python3 tests/run_tests.py --quick    ## skip the slow crash tests
python3 tests/run_tests.py --list     ## the test files
python3 benchmark/bench_contention.py --processes 100 --threads 10   ## contention benchmark
python3 benchmark/bench_ladder.py --markdown results.md              ## 1 to 500 processes x 10 threads
```
The suite includes 10 processes with several threads each fighting over the same files, and crash tests that kill a writer in the middle of a write.

## Documentation
https://bachiraoun.github.io/pyrep/

## Author
Bachir Aoun
