from Exceptions import *
from Syslog import *
from HttpServer import *
from SkynetStorage import *

class DoorLocks():
    def __init__(s, skynet):
        s.skynet = skynet
        s.io = skynet.io
        s.httpServer = skynet.httpServer
        s.conf = skynet.conf.doorLocks

        s.log = Syslog('DoorLocks')
        s.storage = SkynetStorage(skynet, 'door_locks.json')
        s._locks = []
        s.httpHandlers = DoorLocks.HttpHandlers(s)
        s.uiUpdater = s.skynet.periodicNotifier.register("door_locks", s.uiUpdateHandler, 2000)

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


    def destroy(s):
        print('destroy DoorLocks')
        s.storage.destroy()


    class HttpHandlers():
        def __init__(s, manager):
            s.manager = manager
            s.skynet = manager.skynet
            s.regUiHandler('w', "GET", "/doorlooks/on", s.doorlookOnHandler, ('name', ))
            s.regUiHandler('w', "GET", "/doorlooks/off", s.doorlookOffHandler, ('name', ))


        def regUiHandler(s, permissionMode, method, url, handler,
                                requiredFields=[], retJson=True):
            s.skynet.ui.setReqHandler('door_locks', permissionMode, method,
                                       url, handler, requiredFields, retJson)


        def doorlookOnHandler(s, args, conn):
            try:
                name = args['name']
                doorLock = s.manager.doorLock(name)
                doorLock.open()
            except AppError as e:
                raise HttpHandlerError("Can't open door lock %s: %s" % (name, e))


        def doorlookOffHandler(s, args, conn):
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
            s._state = s.manager.storage.key('/lastState/%s' % name, False)
            Task.setPeriodic('doorlooks_actualizer_%s' % name, 1000, s.actualizer_cb)


        def actualizer_cb(s, task):
            try:
                if s._state.val:
                    s.open()
                else:
                    s.close()
            except IoError:
                return
            task.remove()


        def doEventProcessing(s, port, state):
            s.manager.updateUi()


        def name(s):
            return s._name


        def open(s):
            s._port.up()
            s._state.set(True)


        def close(s):
            s._port.down()
            s._state.set(False)


        def isClosed(s):
            return not s._port.state()


        def __repr__(s):
            return "DoorLock:%s" % s.name()

