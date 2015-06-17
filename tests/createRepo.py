import os
from pyrep.Repository import PyrepInfo

PI=PyrepInfo()
PI._update_path(os.path.join(os.getcwd(),'pyrepTest'))

PI.add_directory('bachir/nadine/zouzou')
PI.add_directory('bachir/nadine/7ebbo')
print PI.get_directory('bachir')