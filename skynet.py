import sys
sys.path.append('sr90lib/')
sys.path.append('src/')

from math import *
import rlcompleter, readline
readline.parse_and_bind('tab:complete')
import atexit

from Skynet import *


s = skynet()

def exitCb():
    print("call exitCb")
    skynet.destroy()

atexit.register(exitCb)


io = s.io

print("help:")
print("\tskynet")
print("\tio")