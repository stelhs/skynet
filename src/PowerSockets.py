from Exceptions import *
from Syslog import *


class PowerSockets():
    def __init__(s, skynet):
        s.log = Syslog('PowerSockets')
        s.conf = skynet.conf.powerSockets
        s.io = skynet.io
        s._sockets = []

        for name, inf in s.conf.items():
            dl = PowerSockets.PowerSocket(s, name, inf['description'], inf['port'])
            s._sockets.append(dl)


    def list(s):
        return s._sockets


    def up(s):
        for socket in s.list():
            socket.up()


    def socket(s, name):
        for ps in s.list():
            if ps.name() == name:
                return ps
        raise PowerSocketError(s.log, "Power Socket '%s' is not registred" % name)


    class PowerSocket():
        def __init__(s, manager, name, description, pName):
            s.manager = manager
            s._name = name
            s._description = description
            s._port = s.manager.io.port(pName)


        def name(s):
            return s._name


        def up(s):
            s._port.up()


        def down(s):
            s._port.down()
