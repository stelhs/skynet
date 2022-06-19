from Exceptions import *
from Syslog import *


class DoorLocks():
    def __init__(s, skynet):
        s.log = Syslog('DoorLocks')
        s.conf = skynet.conf.doorLocks
        s.io = skynet.io
        s._locks = []

        for name, inf in s.conf.items():
            dl = DoorLocks.DoorLock(s, name, inf['description'], inf['port'])
            s._locks.append(dl)


    def list(s):
        return s._locks


    def doorLock(s, name):
        for dl in s.list():
            if dl.name() == name:
                return dl
        raise DoorLocksError(s.log, "Door Lock '%s' is not registred" % name)


    class DoorLock():
        def __init__(s, manager, name, description, pName):
            s.manager = manager
            s._name = name
            s._description = description
            s._port = s.manager.io.port(pName)


        def name(s):
            return s._name


        def open(s):
            s._port.up()


        def close(s):
            s._port.down()
