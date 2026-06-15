import threading
from Exceptions import *
from Syslog import *
from Task import *
from HttpServer import *


class Ventilation():
    def __init__(s, skynet):
        s.skynet = skynet
        s.io = skynet.io
        s.tc = skynet.tc
        s.ui = skynet.ui
        s._lock = threading.Lock()
        s.httpServer = skynet.httpServer
        s.httpHandlers = Ventilation.HttpHandlers(s)

        s.log = Syslog("Ventilation")
        s.fanPort = s.io.port('air_fan')
        s.valveOpenPort = s.io.port('air_valve_open')
        s.valveClosePort = s.io.port('air_valve_close')
        s.valveOpenedSense = s.io.port('air_valve_opened')
        s.valveClosedSense = s.io.port('air_valve_closed')

        def fanPortUpdater(state):
            s.skynet.emitEvent('ventilation', 'ledsUpdate',
                               {'ledVentilationEnabled': state})
        s.fanPort.subscribe("Ventilation", fanPortUpdater)

        def valveOpenUpdater(state):
            s.skynet.emitEvent('ventilation', 'ledsUpdate',
                               {'ledVentilationValveOpen': state})
        s.valveOpenPort.subscribe("Ventilation", valveOpenUpdater)

        def valveCloseUpdater(state):
            s.skynet.emitEvent('ventilation', 'ledsUpdate',
                               {'ledVentilationValveClose': state})
        s.valveClosePort.subscribe("Ventilation", valveCloseUpdater)

        def valveOpenedUpdater(state):
            s.skynet.emitEvent('ventilation', 'ledsUpdate',
                               {'ledVentilationValveOpened': state})
        s.valveOpenedSense.subscribe("Ventilation", valveOpenedUpdater)

        def valveClosedUpdater(state):
            s.skynet.emitEvent('ventilation', 'ledsUpdate',
                               {'ledVentilationValveClosed': state})
        s.valveClosedSense.subscribe("Ventilation", valveClosedUpdater)

        s.uiUpdater = s.skynet.periodicNotifier.register("Ventilation", s.uiUpdateHandler, 2000)
        s._busy = False


    def toAdmin(s, msg):
        s.log.err("Ventilation: %s" % msg)
        s.tc.toAdmin("Ventilation: %s" % msg)
        s.ui.logErr("Ventilation", msg)


    def uiUpdateHandler(s):
        data = {}
        try:
            data['ledVentilationEnabled'] = s.fanPort.state()
        except IoError:
            pass

        try:
            data['ledVentilationValveOpened'] = s.valveOpenedSense.state()
        except IoError:
            pass

        try:
            data['ledVentilationValveClosed'] = s.valveClosedSense.state()
        except IoError:
            pass

        try:
            data['ledVentilationValveOpen'] = s.valveOpenPort.state()
        except IoError:
            pass

        try:
            data['ledVentilationValveClose'] = s.valveClosePort.state()
        except IoError:
            pass

        s.skynet.emitEvent('ventilation', 'ledsUpdate', data)


    def isBusy(s):
        return s._busy


    def fanOn(s):
        s.fanPort.up();


    def fanOff(s):
        s.fanPort.down();


    def isFunOn(s):
        return s.fanPort.state()


    def valveOpen(s):
        s._busy = True
        s.valveAbortFlag = False

        if s.valveOpenedSense.state():
            s._busy = False
            return

        s.valveClosePort.down()
        Task.sleep(300)

        s.valveOpenPort.up()
        timeout = now() + 10
        while not s.valveOpenedSense.state():
            if s.valveAbortFlag:
                break
            if now() >= timeout:
                s.valveOpenPort.down()
                s._busy = False
                raise VentilationError(s.log, "Valve opening timeout exceeded")
            Task.sleep(300)

        s.valveOpenPort.down()
        s._busy = False


    def valveClose(s):
        s._busy = True
        s.valveAbortFlag = False

        if s.valveClosedSense.state():
            s._busy = False
            return

        s.valveOpenPort.down()
        Task.sleep(300)

        s.valveClosePort.up()
        timeout = now() + 10
        while not s.valveClosedSense.state():
            if s.valveAbortFlag:
                break
            if now() >= timeout:
                s.valveClosePort.down()
                s._busy = False
                raise VentilationError(s.log, "Valve closing timeout exceeded")
            Task.sleep(300)

        s.valveClosePort.down()
        s._busy = False


    def valveAbort(s):
        s.valveOpenPort.down()
        s.valveClosePort.down()
        s.valveAbortFlag = True


    def isValveOpened(s):
        return s.valveOpenedSense.state()


    def isValveClosed(s):
        return s.valveClosedSense.state()


    def run(s):
        s.valveOpen()
        s.fanOn()


    def stop(s):
        s.fanOff()
        s.valveClose()


    def textStat(s):
        text = "Вентиляция:\n"
        try:
            text += "    Вентилятор: %s\n" % ('включён' if s.isFunOn() else 'отключён')
        except AppError as e:
            text += "    Состояние вентилятора запросить не удалось: %s\n" % e

        try:
            val = "не закрыт"
            if s.isValveOpened():
                val = "открыт";
            elif s.isValveClosed():
                val = "закрыт";
            text += "    Положение клапана: %s\n" % val
        except AppError as e:
            text += "    Положение клапана запросить не удалось: %s\n" % e

        return text


    def destroy(s):
        print("destroy Ventilation")
        try:
            s.fanPort.down()
            s.valveOpenPort.down()
            s.valveClosePort.down()
        except IoError:
            pass


    class HttpHandlers():
        def __init__(s, v):
            s.v = v
            s.skynet = v.skynet
            s.regUiHandler('w', "GET", "/ventilation/power_on", s.powerOnHandler)
            s.regUiHandler('w', "GET", "/ventilation/power_off", s.powerOffHandler)
            s.regUiHandler('w', "GET", "/ventilation/valve_open", s.valveOpenHandler)
            s.regUiHandler('w', "GET", "/ventilation/valve_close", s.valveCloseHandler)


        def regUiHandler(s, permissionMode, method, url, handler,
                                requiredFields=[], retJson=True):
            s.skynet.ui.setReqHandler('ventilation', permissionMode, method,
                                      url, handler, requiredFields, retJson)


        def powerOnHandler(s, args, conn):
            if s.v.isBusy():
                raise HttpHandlerError("Ventilation is busy")
            def do():
                try:
                    s.v.run()
                except AppError as e:
                    s.v.toAdmin('Не удалось запустить вытяжку: %s' % e)
            Task.asyncRunSingle('ventilationPowerOnTask', do)


        def powerOffHandler(s, args, conn):
            if s.v.isBusy():
                raise HttpHandlerError("Ventilation is busy")
            def do():
                try:
                    s.v.stop()
                except AppError as e:
                    s.v.toAdmin('Не удалось остановить вытяжку: %s' % e)
            Task.asyncRunSingle('ventilationPowerOffTask', do)


        def valveOpenHandler(s, args, conn):
            if s.v.isBusy():
                s.v.valveAbort()
                return
            def do():
                try:
                    s.v.valveOpen()
                except AppError as e:
                    s.v.toAdmin('Не удалось открыть вентиляционный клапан: %s' % e)
            Task.asyncRunSingle('ventilationValveOpenTask', do)


        def valveCloseHandler(s, args, conn):
            if s.v.isBusy():
                s.v.valveAbort()
                return
            def do():
                try:
                    s.v.valveClose()
                except AppError as e:
                    s.v.toAdmin('Не удалось закрыть вентиляционный клапан: %s' % e)
            Task.asyncRunSingle('ventilationValveCloseTask', do)





