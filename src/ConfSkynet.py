from ConfParser import *

class ConfSkynet(ConfParser):
    def __init__(s):
        super().__init__()

        s.addConfig('db', 'database.conf')
        s.addConfig('io', 'io.conf')
        s.addConfig('boiler', 'boiler.conf')
        s.addConfig('skynet', 'skynet.conf')
        s.addConfig('telegram', 'telegram.conf')
        s.addConfig('termosensors', 'termosensors.conf')


