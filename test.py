
# standard distribution imports
from __future__ import print_function
import os
import warnings
from pprint import pprint

# numpy imports
import numpy as np

# import Repository
from pyrep import Repository

# initialize Repository instance
REP=Repository()

# create a path pointing to user home
PATH = os.path.join(os.path.expanduser("~"), 'pyrepTest_canBeDeleted')

# check if directory exist
if REP.is_repository(PATH):
    REP.remove_repository(path=PATH, removeEmptyDirs=True)


# print repository path
print("repository path --> %s"%str(REP.path))
print()

# create repository in path
print("\\nIs path '%s' a repository --> %s"%(PATH, str(REP.is_repository(PATH))))
success,message = REP.create_repository(PATH)
assert success, message
print('\\nRepository path --> %s'%str(REP.path))
print()

# add directories
success,message = REP.add_directory("folder1/folder2/folder3")
if not success:
    print(message)

success,message = REP.add_directory("folder1/archive1/archive2/archive3/archive3")
if not success:
    print(message)

success,message = REP.add_directory("directory1/directory2")
if not success:
    print(message)

# dump files
value = "This is a string data to pickle and store in the repository"
success,message = REP.dump_file(value, relativePath='pickled', dump=None, pull=None, replace=True)
if not success:
    print(message)

value = np.random.random(3)
dump="import numpy as np; np.savetxt(fname='$FILE_PATH', X=value, fmt='%.6e')"
pull="import numpy as np; PULLED_DATA=np.loadtxt(fname='$FILE_PATH')"

success,message = REP.dump(value, relativePath='text.dat', dump=dump, pull=pull, replace=True)
if not success:
    print(message)

success,message = REP.dump(value, relativePath="folder1/folder2/folder3/folder3Pickled.pkl", replace=True)
if not success:
    print(message)

success,message = REP.dump(value, relativePath="folder1/archive1/archive1Pickled1", replace=True)
if not success:
    print(message)

success,message = REP.dump(value, relativePath="folder1/archive1/archive1Pickled2", replace=True)
if not success:
    print(message)

success,message = REP.dump(value, relativePath="folder1/archive1/archive2/archive2Pickled1", replace=True)
if not success:
    print(message)

# pull data
data = REP.pull(relativePath='text.dat')
print('\\nPulled text data --> %s'%str(data))
print()

data = REP.pull(relativePath="folder1/folder2/folder3/folder3Pickled.pkl")
print('\\nPulled pickled data --> %s'%str(data))
print()

# update
value = "This is an updated string"
REP.update(value, relativePath='pickled')
print('\\nUpdate pickled data to --> %s'%value)
print()

# walk repository files
print('\\nwalk repository files relative path')
print('------------------------------------')
for f in REP.walk_files_path(recursive=True):
    print(f)
print()

# walk repository, directories
print('\\nwalk repository directories relative path')
print('------------------------------------------')
for d in REP.walk_directories_path(recursive=True):
    print(d)
print()

print('\\nRepository print -->')
print(REP)
print()

print('\\nRepository representation -->')
print(repr(REP))
print()

print('\\nRepository to list -->')
for fdDict in REP.get_repository_state():
    k = list(fdDict)[0]
    print("%s: %s"%(k,str(fdDict[k])))
print()

print('\\nCreate package from repository ...')
REP.create_package(path=None, name=None)
print()

# Try to load
try:
    REP.load_repository(PATH)
except:
    loadable = False
finally:
    loadable = True
print('\\nIs repository loadable -->',loadable)
print()

print('\\Copy folder1 to copied_folder1 ...')
import time
p0 = 'folder1'
p1 = 'copied_folder1'
for i in range(1,11):
    tic = time.time()
    REP.copy_directory(relativePath=p0, newRelativePath=p1, overwrite=True, raiseError=True)
    p1 = os.path.join('copied_folder%i'%(i+1),p1)
    print(time.time()-tic)
print(REP)
# remove all repo data
#REP.remove_repository(removeEmptyDirs=True)

# check if there is a repository in path
print( "\\nIs path '%s' a repository --> %s"%(PATH, str(REP.is_repository(PATH))) )
print()


"""
from __future__ import print_function
import os, random
from pprint import pprint
from pyrep import Repository

path = os.path.join( os.path.expanduser('~'), 'pyrep_test')
R = Repository()
success, message = R.create_repository(path, replace=True)
if not success:
    print(message)

#R.load_repository(path, verbose=True)


success, message = R.add_directory(relativePath='first/second/third_1', description='here you go', clean=True)
if not success:
    print(message)

success, message = R.add_directory(relativePath='first/second/third_2', description='here you go', clean=True)
if not success:
    print(message)

success, message = R.add_directory(relativePath='first/second/third_3', description='here you go', clean=True)
if not success:
    print(message)

#pprint(R.get_repository_state())
success, message = R.rename_directory(relativePath='first/second/third_3', newName='another_directory_name')
if not success:
    print(message)

#pprint(R.get_repository_state())
#pprint(R._Repository__repo)
#pprint(R.get_repository_state())

success, error = R.remove_directory(relativePath='first/second/third_2')
if not success:
    print(error)


#pprint(R.get_repository_state())

success, error = R.dump_file(value=[random.random() for _ in range(10)],relativePath='range', dump='numpy')
if not success:
    print(error)

data = R.pull_file(relativePath='range')
print(data)


success, error = R.update_file(value=[random.random() for _ in range(5)],relativePath='range')
if not success:
    print(error)

data = R.pull_file(relativePath='range')
print(data)

success, error = R.rename_file(relativePath='range', newRelativePath='p1/p2/p3/thisisit.txt')
if not success:
    print(error)

data = R.pull_file(relativePath='p1/p2/p3/thisisit.txt')
print(data)

success, error = R.dump_file(value=[random.random() for _ in range(10)],relativePath='p1/range1', dump='numpy')
if not success:
    print(error)

success, error = R.dump_file(value=[random.random() for _ in range(10)],relativePath='range2', dump='numpy')
if not success:
    print(error)

print(R)
a = str(R)
print('lol',a)


for dpath, info in R.walk_files_info('', recursive=True):
    print(dpath, end='\n'+'='*len(dpath)+'\n')
    pprint(info)
    print()

for dpath, info in R.walk_directories_info('', recursive=True):
    print(dpath, end='\n'+'='*len(dpath)+'\n')
    pprint(info)
    print()
"""
