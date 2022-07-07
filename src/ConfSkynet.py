from ConfParser import *

class ConfSkynet(ConfParser):
    def __init__(s):
        super().__init__()

        s.addConfig('db', 'database.conf')
        s.addConfig('users', 'users.conf')
        s.addConfig('io', 'io.conf')
        s.addConfig('boiler', 'boiler.conf')
        s.addConfig('skynet', 'skynet.conf')
        s.addConfig('telegram', 'telegram.conf')
        s.addConfig('termosensors', 'termosensors.conf')
        s.addConfig('doorLocks', 'door_locks.conf')
        s.addConfig('powerSockets', 'power_sockets.conf')
        s.addConfig('lighters', 'lighters.conf')
        s.addConfig('guard', 'guard.conf')
        s.addConfig('waterSupply', 'water_supply.conf')



