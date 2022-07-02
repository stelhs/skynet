from Exceptions import *
from Syslog import *
from HttpServer import *


class PowerSockets():
    def __init__(s, skynet):
        s.skynet = skynet
        s.log = Syslog('PowerSockets')
        s.conf = skynet.conf.powerSockets
        s.io = skynet.io
        s.httpServer = skynet.httpServer
        s._sockets = []
        s.httpHandlers = PowerSockets.HttpHandlers(s)
        s.uiUpdater = s.skynet.ui.periodicNotifier.register("power_sockets", s.uiUpdateHandler, 2000)

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



    class HttpHandlers():
        def __init__(s, manager):
            s.manager = manager
            s.hs = manager.httpServer
            s.hs.setReqHandler("GET", "/power_sockets/on", s.powerOnHandler, ('name', ))
            s.hs.setReqHandler("GET", "/power_sockets/off", s.powerOffHandler, ('name', ))


        def powerOnHandler(s, args, body, attrs, conn):
            try:
                name = args['name']
                socket = s.manager.socket(name)
                socket.up()
            except AppError as e:
                raise HttpHandlerError("Can't power on for socket %s: %s" % (name, e))


        def powerOffHandler(s, args, body, attrs, conn):
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
            s._port = s.manager.io.port(pName)
            s._port.subscribe("PowerSocket", lambda state: s.manager.uiUpdater.call())


        def name(s):
            return s._name


        def up(s):
            s._port.up()


        def down(s):
            s._port.down()


        def isDown(s):
            return not s._port.cachedState()


        def __repr__(s):
            return "PowerSocket:%s" % s.name()

