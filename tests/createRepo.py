import numpy as np
from pyrep.Repository import Repository

REP=Repository()
print "repository path --> %s"%str(REP.path)
REP.remove_repository(".")
print "Is path '.' a repository --> %s"%str(REP.is_repository('.'))
REP.initialize(path='.', replace=True, save=True)
print "Repository initialized, is path '.' a repository --> %s"%str(REP.is_repository('.'))
print 'repository path --> %s'%str(REP.path)

# add directory
REP.add_directory("folder1/folder2/folder3")
REP.add_directory("folder1/archive1/archive2")
REP.add_directory("directory1/directory2")

# dump files
file = "This is a string data to pickle and store in the repository"
REP.dump_file(file, relativePath='.', name='pickled', dump=None, pull=None, replace=True, save=True)

file = np.random.random(3)
dump="import numpy as np; np.savetxt(fname='$FILE_PATH', X=file, fmt='%.6e')"
pull="import numpy as np; PULLED_DATA=np.loadtxt(fname='$FILE_PATH')"
REP.dump_file(file, relativePath='.', name='text', dump=dump, pull=pull, replace=True, save=True)

# pull data
data = REP.pull_file(relativePath='.', name='text')
print 'Pulled text data --> %s'%str(data)
data = REP.pull_file(relativePath='.', name='pickled')
print 'Pulled pickled data --> %s'%str(data)

# get repository info tree
#print 'repository info --> %s'%str(REP.get_directory_info(''))