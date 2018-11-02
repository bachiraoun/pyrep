from __future__ import print_function
import os
from pprint import pprint
from pyrep import Repository

path = os.path.join( os.path.expanduser('~'), 'pyrep_test')
R = Repository()
success, message = R.create_repository(path, replace=True)
if not success:
    print(message)

success, message = R.add_directory(relativePath='first/second/third_1', info='here you go', clean=True)
if not success:
    print(message)

success, message = R.add_directory(relativePath='first/second/third_2', info='here you go', clean=True)
if not success:
    print(message)

success, message = R.add_directory(relativePath='first/second/third_3', info='here you go', clean=True)
if not success:
    print(message)

#pprint(R.get_repository_state())
success, message = R.rename_directory(relativePath='first/second/third_3', newName='another_name')
if not success:
    print(message)

#pprint(R.get_repository_state())
#pprint(R._Repository__repo)
#pprint(R.get_repository_state())

success, error = R.remove_directory(relativePath='first/second/third_2')
if not success:
    print(error)



success, error = R.dump_file(value=range(10),relativePath='range', pull='numpy_text', dump='numpy_text')
if not success:
    print(error)


#success, errors = R.clean_before_after(R.get_repository_list_representation(), [])
#if not success:
#    print('\n'.join(errors))
#success, message = R.remove_directory(relativePath='lol/me/lil', clean=True)
#if not success:
#    print(message)
