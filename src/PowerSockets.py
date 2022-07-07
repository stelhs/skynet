from Exceptions import *
from Syslog import *
from HttpServer import *
from Storage import *


class PowerSockets():
    def __init__(s, skynet):
        s.skynet = skynet
        s.io = skynet.io
        s.conf = skynet.conf.powerSockets
        s.httpServer = skynet.httpServer
        s.storage = Storage('power_sockets.json')
        s.log = Syslog('PowerSockets')
        s._sockets = []
        s.httpHandlers = PowerSockets.HttpHandlers(s)
        s.uiUpdater = s.skynet.periodicNotifier.register("power_sockets", s.uiUpdateHandler, 2000)

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


    def uiUpdateHandler(s):
        data = {}
        for ps in s.list():
            try:
                data[ps.name()] = not ps.isDown()
            except AppError:
                pass
        s.skynet.emitEvent('power_sockets', 'statusUpdate', data)


    def destroy(s):
        print('destroy PowerSockets')
        s.storage.destroy()


    class HttpHandlers():
        def __init__(s, manager):
            s.manager = manager
            s.skynet = manager.skynet
            s.regUiHandler('w', "GET", "/power_sockets/on", s.powerOnHandler, ('name', ))
            s.regUiHandler('w', "GET", "/power_sockets/off", s.powerOffHandler, ('name', ))


        def regUiHandler(s, permissionMode, method, url, handler,
                                requiredFields=[], retJson=True):
            s.skynet.ui.setReqHandler('power_sockets', permissionMode, method,
                                       url, handler, requiredFields, retJson)


        def powerOnHandler(s, args, conn):
            try:
                name = args['name']
                socket = s.manager.socket(name)
                socket.up()
            except AppError as e:
                raise HttpHandlerError("Can't power on for socket %s: %s" % (name, e))


        def powerOffHandler(s, args, conn):
            try:
                name = args['name']
                socket = s.manager.socket(name)
                socket.down()
            except AppError as e:
                raise HttpHandlerError("Can't power off for socket %s: %s" % (name, e))



    class PowerSocket():
        def __init__(s, manager, name, description, pName):
            s.manager = manager
            s._name = name
            s._description = description
            s._state = s.manager.storage.key('/lastState/%s' % name, False)
            s._port = s.manager.io.port(pName)
            s._port.subscribe("PowerSocket", lambda state: s.manager.uiUpdater.call())

            if s._state.val:
                s.up()
            else:
                s.down()


        def name(s):
            return s._name


        def up(s):
            s._port.up()
            s._state.set(True)


        def down(s):
            s._port.down()
            s._state.set(False)


        def isDown(s):
            return not s._port.cachedState()


        def __repr__(s):
            return "PowerSocket:%s" % s.name()

