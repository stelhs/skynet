from Exceptions import *
from Syslog import *
from HttpServer import *
from SkynetStorage import *


class PowerSockets():
    def __init__(s, skynet):
        s.skynet = skynet
        s.io = skynet.io
        s.conf = skynet.conf.powerSockets
        s.httpServer = skynet.httpServer
        s.storage = SkynetStorage(skynet, 'power_sockets.json')
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
                data['ledPowerZone_%s' % ps.name()] = not ps.isDown()
            except IoError:
                pass
        s.skynet.emitEvent('power_sockets', 'ledsUpdate', data)


    def textStat(s):
        text = "Наличие питания:\n"
        for ps in s.list():
            try:
                text += "    %s: %s\n" % (ps.description(), 'отсуствует' if ps.isDown() else 'присутвует')
            except AppError as e:
                text += "    Состояние питания зоны '%s' запросить не удалось: %s" % (ps.description(), e)
        return text


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

            Task.setPeriodic('power_socket_actualizer_%s' % name, 1000, s.actualizer_cb)


        def actualizer_cb(s, task):
            try:
                if s._state.val:
                    s.up()
                else:
                    s.down()
            except IoError:
                return
            task.remove()


        def name(s):
            return s._name


        def description(s):
            return s._description


        def up(s):
            s._port.up()
            s._state.set(True)


        def down(s):
            s._port.down()
            s._state.set(False)


        def isDown(s):
            return not s._port.state()


        def __repr__(s):
            return "PowerSocket:%s" % s.name()

