from Exceptions import *
from Syslog import *
from HttpServer import *

class DoorLocks():
    def __init__(s, skynet):
        s.skynet = skynet
        s.log = Syslog('DoorLocks')
        s.conf = skynet.conf.doorLocks
        s.io = skynet.io
        s.httpServer = skynet.httpServer
        s._locks = []
        s.httpHandlers = DoorLocks.HttpHandlers(s)
        s.uiUpdater = s.skynet.ui.periodicNotifier.register("door_locks", s.uiUpdateHandler, 2000)

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


    def uiUpdateHandler(s):
        data = {}
        for dl in s.list():
            try:
                data[dl.name()] = not dl.isClosed()
            except AppError:
                pass
        s.skynet.emitEvent('door_locks', 'statusUpdate', data)


    class HttpHandlers():
        def __init__(s, manager):
            s.manager = manager
            s.hs = manager.httpServer
            s.hs.setReqHandler("GET", "/doorlooks/on", s.doorlookOnHandler, ('name', ))
            s.hs.setReqHandler("GET", "/doorlooks/off", s.doorlookOffHandler, ('name', ))


        def doorlookOnHandler(s, args, body, attrs, conn):
            try:
                name = args['name']
                doorLock = s.manager.doorLock(name)
                doorLock.open()
            except AppError as e:
                raise HttpHandlerError("Can't open door lock %s: %s" % (name, e))


        def doorlookOffHandler(s, args, body, attrs, conn):
            try:
                name = args['name']
                doorLock = s.manager.doorLock(name)
                doorLock.close()
            except AppError as e:
                raise HttpHandlerError("Can't close door lock %s: %s" % (name, e))


    class DoorLock():
        def __init__(s, manager, name, description, pName):
            s.manager = manager
            s._name = name
            s._description = description
            s._port = s.manager.io.port(pName)
            s._port.subscribe("DoorLock", lambda state: s.manager.uiUpdater.call())


        def doEventProcessing(s, port, state):
            s.manager.updateUi()


        def name(s):
            return s._name


        def open(s):
            s._port.up()


        def close(s):
            s._port.down()


        def isClosed(s):
            return not s._port.cachedState()


        def __repr__(s):
            return "DoorLock:%s" % s.name()
