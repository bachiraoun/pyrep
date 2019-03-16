# standard distribution imports
from __future__ import print_function
import sys, os, time, datetime, random

# numpy imports
import numpy as np

# import Repository
from pyrep import Repository

# set IGNORE_REP
IGNORE_DIR_NOT_REP = True

SLEEP = 0.001
MODES = ["save_repository","load_repository", "update_string_pickled", "dump_string_pickled"]
FORCE_MODE = None

if len(sys.argv)>1:
    for m in sys.argv[1:]:
        assert m in MODES, "given mode '%s' is not in modes"%(m,)
    MODES = sys.argv[1:]
    #print(MODES)

# initialize Repository instance
REP=Repository()

# create a path pointing to user home
PATH = os.path.join(os.path.expanduser("~"), 'pyrepTest_multi_processes')

# check if directory exist
create = False
if os.path.isdir(PATH):
    if not REP.is_repository(PATH):
        if not IGNORE_DIR_NOT_REP:
            warnings.warn("Directory exists and it's not a pyrep repository. Set IGNORE_DIR_NOT_REP to True.")
            exit()
        REP.create_repository(PATH)
        create = True
    else:
        REP.load_repository(PATH)
else:
    REP.create_repository(PATH)
    create = True

# add directories
if create:
    print(1)
    REP.add_directory("folder_11/folder_12/folder_13")
    print(2)
    REP.add_directory("folder_21/folder_22/folder_23")
    print(3)
    REP.add_directory("folder_31/folder_32/folder_33")
    print(4)

    # dump files
    value = "This is a string data to pickle and store in the repository"
    REP.dump_file(value, relativePath='string_pickled', dump=None, pull=None, replace=True)


    value = np.random.random(500)
    dump="import numpy as np; np.savetxt(fname='$FILE_PATH', X=value, fmt='%.6e')"
    pull="import numpy as np; PULLED_DATA=np.loadtxt(fname='$FILE_PATH')"
    REP.dump(value, relativePath='array.dat',  dump=dump, pull=pull, replace=True)
    REP.dump(value, relativePath='folder_11/array.pickled', dump=dump, pull=pull, replace=True)

    print(REP)


while True:
    time.sleep(SLEEP)
    tic = time.time()
    if FORCE_MODE is None:
        mode = random.choice(MODES)
    else:
        mode = FORCE_MODE
    if mode == 'load_repository':
        _ = Repository().load_repository(PATH)
    elif mode == "save_repository":
        REP.save()
    elif mode == "update_string_pickled":
        value = "This is a string data to pickle and store in the repository"
        REP.update_file(value, relativePath='string_pickled', dump=None, pull=None)
    elif mode == "dump_string_pickled":
        value = "This is a string data to pickle and store in the repository"
        REP.dump_file(value, relativePath='string_pickled', dump=None, pull=None, replace=True)
    #print(str(datetime.datetime.now()), rep.len)
    print(time.time()-tic, mode)
