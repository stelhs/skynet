import threading
from Exceptions import *
from Syslog import *
from HttpServer import *

class Gates():
    def __init__(s, skynet):
        s.skynet = skynet
        s.io = skynet.io
        s.tc = skynet.tc
        s._lock = threading.Lock()
        s.log = Syslog("Gates")
        s.powerPort = s.io.port('gates_power')
        s.closePort = s.io.port('gates_close')
        s.openPort = s.io.port('gates_open')
        s.openPedPort = s.io.port('gates_open_pedestration')
        s.isClosedPort = s.io.port('gates_closed')

        s.buttRemoteGuardSleepPort = s.io.port('remote_guard_sleep')
        s.buttRemoteOpenClosePort = s.io.port('remote_gates_open_close')
        s.buttOpenCloseWorkshopPort = s.io.port('gates_op_cl_workshop')

        s.httpServer = skynet.httpServer
        s.httpHandlers = Gates.HttpHandlers(s)
        s.TgHandlers = Gates.TgHandlers(s)

        s.lastRemoteButton = 'open'

        s.buttRemoteGuardSleepPort.subscribe('Gates', s.buttOpenCloseHandler, 1)
        s.buttOpenCloseWorkshopPort.subscribe('Gates', s.buttOpenCloseHandler, 1)
        s.buttRemoteOpenClosePort.subscribe('Gates', s.buttOpenClosePedHandler, 1)
        s.isClosedPort.subscribe('Gates', s.senseGatesClosedHandler)
        s.powerPort.subscribe('Gates', lambda state: s.uiUpdater.call())
        s.isClosedPort.subscribe('Gates', lambda state: s.uiUpdater.call())

        s.uiUpdater = s.skynet.periodicNotifier.register("gates", s.uiUpdateHandler, 2000)


    def uiUpdateHandler(s):
        data = {}
        try:
            data['gatesClosed'] = s.isClosedPort.cachedState()
        except IoPortCachedStateExpiredError:
            pass
        try:
            data['gatesPower'] = not s.powerPort.cachedState()
        except IoPortCachedStateExpiredError:
            pass
        s.skynet.emitEvent('gates', 'statusUpdate', data)


    def open(s):
        with s._lock:
            if not s.isPowerEnabled():
                raise GatesNoPowerError(s.log, "Can't open gates. Power is absent")
            s.closePort.down()
            s.openPort.blink(1000, 500, 1)


    def openPed(s):
        with s._lock:
            if not s.isPowerEnabled():
                raise GatesNoPowerError(s.log, "Can't open gates. Power is absent")
            s.closePort.down()
            s.openPedPort.blink(1000, 500, 1)


    def close(s):
        with s._lock:
            if not s.isPowerEnabled():
                raise GatesNoPowerError(s.log, "Can't open gates. Power is absent")
            if s.isClosed():
                return
            s.openPort.down()
            s.closePort.blink(1000, 500, 1)


    def isClosed(s):
        return s.isClosedPort.state()


    def powerDisable(s):
        s.powerPort.up()


    def powerEnable(s):
        s.powerPort.down()


    def isPowerEnabled(s):
        return not s.powerPort.state()


    def buttOpenCloseHandler(s, state):
        if s.skynet.guard.isStarted():
            return

        s.io.port('guard_lamp').blink(200, 200, 2)

        if s.isClosed():
            s.lastRemoteButton = 'open'
            return s.open()

        if s.lastRemoteButton == 'open':
            s.lastRemoteButton = 'close'
            return s.close()

        s.lastRemoteButton = 'close'
        return s.open()


    def buttOpenClosePedHandler(s, state):
        if s.guard.isStarted():
            return

        s.io.port('guard_lamp').blink(200, 200, 1)

        if s.isClosed():
            return s.openPed()

        s.close()


    def senseGatesClosedHandler(s, state):
        if state:
            s.log.info('gates closed')
            s.tc.toAdmin("Ворота закрылись")
            return
        s.log.info('gates opened')
        s.tc.toAdmin("Ворота открылись")





    class HttpHandlers():
        def __init__(s, gates):
            s.gates = gates
            s.skynet = gates.skynet
            s.regUiHandler('w', "GET", "/gates/open", s.openHandler)
            s.regUiHandler('w', "GET", "/gates/close", s.closeHandler)
            s.regUiHandler('w', "GET", "/gates/open_pedestrian", s.openPedestrianHandler)


        def regUiHandler(s, permissionMode, method, url, handler,
                                requiredFields=[], retJson=True):
            s.skynet.ui.setReqHandler('gates', permissionMode, method,
                                      url, handler, requiredFields, retJson)


        def openHandler(s, args, conn):
            try:
                s.gates.open()
            except AppError as e:
                raise HttpHandlerError("Can't open gates: %s" % e)


        def closeHandler(s, args, conn):
            try:
                s.gates.close()
            except AppError as e:
                raise HttpHandlerError("Can't close gates: %s" % e)


        def openPedestrianHandler(s, args, conn):
            try:
                s.gates.openPed()
            except AppError as e:
                raise HttpHandlerError("Can't open gates for pedestrian : %s" % e)


    class TgHandlers():
        def __init__(s, gates):
            s.gates = gates
            s.tc = gates.tc

            s.tc.registerHandler('gates', s.open, 'w', ('открой ворота', 'gates open'))
            s.tc.registerHandler('gates', s.openPed, 'w', ('открой пешеходу', 'gates open ped'))
            s.tc.registerHandler('gates', s.close, 'w', ('закрой ворота', 'gates close'))


        def open(s, arg, replyFn):
            try:
                s.gates.open()
            except AppError as e:
                return replyFn("Не удалось открыть ворота: %s" % e)
            replyFn("Ворота открываются")


        def openPed(s, arg, replyFn):
            try:
                s.gates.openPed()
            except AppError as e:
                return replyFn("Не удалось открыть ворота: %s" % e)
            replyFn("Ворота открываются")


        def close(s, arg, replyFn):
            try:
                s.gates.close()
            except AppError as e:
                return replyFn("Не удалось закрыть ворота: %s" % e)
            replyFn("Ворота закрываются")

