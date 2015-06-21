import numpy as np
from pyrep.Repository import Repository

PATH = '~/Desktop/test'

REP=Repository()
print "repository path --> %s"%str(REP.path)
REP.remove_repository(path=PATH, relatedFiles=False, relatedFolders=False)
REP.create_repository(PATH)
print "\nIs path '.' a repository --> %s"%str(REP.is_repository('.'))
#REP.initialize(path='.', replace=True, save=True)
print "\nRepository initialized, is path '.' a repository --> %s"%str(REP.is_repository('.'))
print '\nRepository path --> %s'%str(REP.path)

# add directory
REP.add_directory("folder1/folder2/folder3")
REP.add_directory("folder1/archive1/archive2/archive3/archive3")
REP.add_directory("directory1/directory2")


# dump files
file = "This is a string data to pickle and store in the repository"
REP.dump_file(file, relativePath='.', name='pickled', dump=None, pull=None, replace=True, save=True)

file = np.random.random(3)
dump="import numpy as np; np.savetxt(fname='$FILE_PATH', X=file, fmt='%.6e')"
pull="import numpy as np; PULLED_DATA=np.loadtxt(fname='$FILE_PATH')"
REP.dump_file(file, relativePath='.', name='text', dump=dump, pull=pull, replace=True, save=True)
REP.dump_file(file, relativePath="folder1/folder2/folder3", name='folder3Pickled', replace=True, save=True)
REP.dump_file(file, relativePath="folder1/archive1", name='archive1Pickled1', replace=True, save=True)
REP.dump_file(file, relativePath="folder1/archive1", name='archive1Pickled2', replace=True, save=True)
REP.dump_file(file, relativePath="folder1/archive1/archive2", name='archive2Pickled1', replace=True, save=True)

# pull data
data = REP.pull_file(relativePath='.', name='text')
print '\nPulled text data --> %s'%str(data)
data = REP.pull_file(relativePath='.', name='pickled')
data = REP.pull_file(relativePath="folder1/folder2/folder3", name='folder3Pickled')
print '\nPulled pickled data --> %s'%str(data)

# walk repository
print '\nwalk files -->', list(REP.walk_files())
print '\nwalk folders -->', list(REP.walk_directories())

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



