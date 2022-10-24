import threading
from Exceptions import *
from Syslog import *
from SkynetStorage import *
from Task import *
from HttpServer import *


class WaterSupply():
    def __init__(s, skynet):
        s.skynet = skynet
        s.conf = skynet.conf.waterSupply
        s.io = skynet.io
        s.tc = skynet.tc
        s._lock = threading.Lock()
        s._autoStopTask = None
        s.httpServer = skynet.httpServer
        s.httpHandlers = WaterSupply.HttpHandlers(s)

        s.log = Syslog("WaterSupply")
        s.pumpPort = s.io.port('water_pump')
        s.lowPressureSense = s.io.port('water_low_pressure')
        s.buttRP = s.io.port('RP_water_pump_button')
        s.buttWorkshop = s.io.port('workshop_water_pump_button')

        s.lowPressureSense.subscribe("WaterSupply", s.lowPressureHandler)
        s.buttWorkshop.subscribe("WaterSupply", s.buttPressedHandler, 1)
        s.buttRP.subscribe("WaterSupply", s.buttPressedHandler, 1)

        s.pumpPort.subscribe("WaterSupply", lambda state: s.uiUpdater.call())
        s.lowPressureSense.subscribe("WaterSupply", lambda state: s.uiUpdater.call())

        s.storage = SkynetStorage(skynet, 'water_supply.json')
        s._enableAutomatic = s.storage.key('/automatic', True)
        s._isBlocked = s.storage.key('/blocked', False)

        s.wcc = WaterSupply.WaterConsumptionChecker(s)
        s.uiUpdater = s.skynet.periodicNotifier.register("water_supply", s.uiUpdateHandler, 2000)


    def toAdmin(s, msg):
        s.log.err("WaterSupply: %s" % msg)
        s.tc.toAdmin("WaterSupply: %s" % msg)


    def uiUpdateHandler(s):
        data = {}
        try:
            data['ledWaterPumpEnabled'] = s.pumpPort.state()
        except IoError:
            pass

        try:
            data['ledWatersupplyLowPressure'] = s.isLowPressure()
        except IoError:
            pass

        data['ledWatersupplyPumpIsLocked'] = s.isBlocked()
        data['ledWatersupplyAutomaticEnabled'] = s._enableAutomatic.val
        s.skynet.emitEvent('water_supply', 'ledsUpdate', data)


    def unlock(s):
        s._isBlocked.set(False)

        if not s._enableAutomatic.val:
            return
        if s.isLowPressure():
            s.pumpRun()


    def lock(s):
        s._isBlocked.set(True)
        s.pumpStop()


    def isBlocked(s):
        return s._isBlocked.val


    def isLowPressure(s):
        return s.lowPressureSense.state()


    def pumpRun(s):
        if s.isBlocked():
            raise PumpIsBlockedError(s.log, "Can't run pump. Pump is blocked")
        s.pumpPort.up()


    def restartAutoStop(s):
        t = None
        s.cancelAutoStop()

        def autostop():
            while 1:
                try:
                    s.pumpPort.down()
                    with s._lock:
                        s._autoStopTask = None
                    return
                except IoError:
                    Task.sleep(1000)


        t = Task.setTimeout("waterSupplyAutoStopTimeout",
                            int(s.conf['pump_run_timeout']) * 1000, autostop)

        with s._lock:
            s._autoStopTask = t


    def cancelAutoStop(s):
        with s._lock:
            if s._autoStopTask:
                s._autoStopTask.remove()
                s._autoStopTask = None


    def pumpStop(s):
        s.cancelAutoStop()
        try:
            s.pumpPort.down()
        except IoError:
            def stop():
                while 1:
                    try:
                        s.pumpPort.down()
                        return
                    except IoError as e:
                        Task.sleep(1000)
            Task.asyncRunSingle('waterSupplyStopper', stop)


    def isStarted(s):
        return s.pumpPort.state()


    def buttPressedHandler(s, state):
        if s.isBlocked():
            s.toAdmin('Нажали на кнопку включения воды, но водообеспечение отключено')

        try:
            if s.isStarted():
                s.pumpStop()
            else:
                s.pumpRun()
        except (IoError, PumpIsBlockedError) as e:
            s.toAdmin('Can`t start/stop water by button pressed: %s' % e)


    def lowPressureHandler(s, state):
        if not s._enableAutomatic.val:
            return

        if s.isBlocked():
            return

        if state == 0:
            s.restartAutoStop()
            return

        if state == 1:
            def start():
                while 1:
                    try:
                        s.pumpRun()
                        return
                    except (IoError, PumpIsBlockedError) as e:
                        Task.sleep(1000)
            Task.asyncRunSingle('waterSupplyAutoStarter', start)
            return



    def destroy(s):
        print("destroy WaterSupply")
        try:
            s.pumpPort.down()
        except IoError:
            pass

        s.storage.destroy()
        s.wcc.destroy()


    class WaterConsumptionChecker():
        def __init__(s, ws):
            s.ws = ws
            s.task = Task.setPeriodic('waterConsumptionChecker', 1000, s.tick)
            s.totalCnt = 0
            s.enabledCnt = 0


        def tick(s, task):
            try:
                if s.ws.isStarted():
                    s.enabledCnt += 1
            except IoError:
                pass

            if s.enabledCnt:
                s.totalCnt += 1

            s.checkForOverrun()


        def checkForOverrun(s):
            if s.totalCnt < 3600:
                return
            s.totalCnt = 0

            if s.enabledCnt < 3000:
                s.enabledCnt = 0
                return

            s.enabledCnt = 0
            try:
                msg = 'В данный момент вода: %s' % (
                      'включена' if s.ws.isStarted() else 'отключена')
            except IoError:
                pass
            s.ws.toAdmin('Зафиксирован высокий расход воды ' \
                         'за прошедший час. ' + msg)


        def destroy(s):
            s.task.remove()


    class HttpHandlers():
        def __init__(s, ws):
            s.ws = ws
            s.skynet = ws.skynet
            s.regUiHandler('w', "GET", "/water_supply/pump_on", s.pumpOnHandler)
            s.regUiHandler('w', "GET", "/water_supply/pump_off", s.pumpOffHandler)
            s.regUiHandler('w', "GET", "/water_supply/switch_automatic_control", s.autoControlSwitchHandler)
            s.regUiHandler('w', "GET", "/water_supply/switch_lock_unlock", s.lockUnlockSwitchHandler)


        def regUiHandler(s, permissionMode, method, url, handler,
                                requiredFields=[], retJson=True):
            s.skynet.ui.setReqHandler('water_supply', permissionMode, method,
                                      url, handler, requiredFields, retJson)


        def pumpOnHandler(s, args, conn):
            try:
                s.ws.pumpRun()
            except AppError as e:
                raise HttpHandlerError("Can't start water pump: %s" % e)


        def pumpOffHandler(s, args, conn):
            try:
                s.ws.pumpStop()
            except AppError as e:
                raise HttpHandlerError("Can't stop water pump: %s" % e)


        def autoControlSwitchHandler(s, args, conn):
            if s.ws._enableAutomatic.val:
                s.ws._enableAutomatic.set(False)
                s.ws.pumpStop()
            else:
                s.ws._enableAutomatic.set(True)
                if s.ws.isLowPressure():
                    s.ws.pumpRun()
            s.ws.uiUpdater.call()


        def lockUnlockSwitchHandler(s, args, conn):
            if s.ws.isBlocked():
                s.ws.unlock()
            else:
                s.ws.lock()
            s.ws.uiUpdater.call()





