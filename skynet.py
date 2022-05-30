import sys
sys.path.append('src/')

from math import *
import rlcompleter, readline
readline.parse_and_bind('tab:complete')
import atexit

from Skynet import *


skynet = Skynet()

def exitCb():
    print("call exitCb")
    skynet.destroy()

atexit.register(exitCb)


io = skynet.subsystemByName('io')

print("help:")
print("\tskynet")
print("\tio")