# standard distribution imports
import os
import warnings

# numpy imports
import numpy as np

# import Repository
from pyrep import Repository

# set IGNORE_REP
IGNORE_DIR_NOT_REP = True

# initialize Repository instance
REP=Repository()

# create a path pointing to user home
PATH = os.path.join(os.path.expanduser("~"), 'pyrepTest_canBeDeleted')

# check if directory exist
if os.path.isdir(PATH):
    if not REP.is_repository(PATH):
        if not IGNORE_DIR_NOT_REP:
            warnings.warn("Directory exists and it's not a pyrep repository. Set IGNORE_DIR_NOT_REP to True.")
            exit()
    else:
        # remove repository from directory if repository exist.
        REP.remove_repository(path=PATH, relatedFiles=False, relatedFolders=False)


# print repository path
print "repository path --> %s"%str(REP.path)

# create repository in path
print "\nIs path '%s' a repository --> %s"%(PATH, str(REP.is_repository(PATH)))
REP.create_repository(PATH)
print '\nRepository path --> %s'%str(REP.path)

# add directories
REP.add_directory("folder1/folder2/folder3")
REP.add_directory("folder1/archive1/archive2/archive3/archive3")
REP.add_directory("directory1/directory2")

# dump files
value = "This is a string data to pickle and store in the repository"
REP.dump_file(value, relativePath='.', name='pickled', dump=None, pull=None, replace=True)

value = np.random.random(3)
dump="import numpy as np; np.savetxt(fname='$FILE_PATH', X=value, fmt='%.6e')"
pull="import numpy as np; PULLED_DATA=np.loadtxt(fname='$FILE_PATH')"
REP.dump(value, relativePath='.', name='text.dat', dump=dump, pull=pull, replace=True)
REP.dump(value, relativePath="folder1/folder2/folder3", name='folder3Pickled.pkl', replace=True)
REP.dump(value, relativePath="folder1/archive1", name='archive1Pickled1', replace=True)
REP.dump(value, relativePath="folder1/archive1", name='archive1Pickled2', replace=True)
REP.dump(value, relativePath="folder1/archive1/archive2", name='archive2Pickled1', replace=True)

# pull data
data = REP.pull(relativePath='.', name='text.dat')
print '\nPulled text data --> %s'%str(data)

data = REP.pull(relativePath="folder1/folder2/folder3", name='folder3Pickled.pkl')
print '\nPulled pickled data --> %s'%str(data)

# update
value = "This is an updated string"
REP.update(value, relativePath='.', name='pickled')
print '\nUpdate pickled data to --> %s'%value

data = REP.pull(relativePath='.', name='pickled')
print '\nPull updated pickled data --> %s'%str(data)

# walk repository files
print '\nwalk repository files relative path'
print '------------------------------------'
for f in REP.walk_files_relative_path():
    print f

# walk repository, directories
print '\nwalk repository directories relative path'
print '------------------------------------------'
for d in REP.walk_directories_relative_path():
    print d


print '\nRepository print -->'
print REP

print '\nRepository representation -->'
print repr(REP)

print '\nRepository to list -->'
print  REP.get_list_representation()
REP.create_package(path=None, name=None)

# Try to load
try:
    REP.load(PATH)
except:
    loadable = False
finally:
    loadable = True
print '\nIs repository loadable -->',loadable 

# remove all repo data
REP.remove_repository(relatedFiles=True, relatedFolders=True)

# check if there is a repository in path
print "\nIs path '%s' a repository --> %s"%(PATH, str(REP.is_repository(PATH)))



