import threading
from Exceptions import *
from Syslog import *
from Storage import *
from Task import *
from HttpServer import *


class WaterSupply():
    def __init__(s, skynet):
        s.skynet = skynet
        s.conf = skynet.conf.waterSupply
        s.io = skynet.io
        s.tc = skynet.tc
        s._lock = threading.Lock()
        s._timeoutTask = None
        s.httpServer = skynet.httpServer
        s.httpHandlers = WaterSupply.HttpHandlers(s)

        s.log = Syslog("WaterSupply")
        s.pumpPort = s.io.port('water_pump')
        s.lowPressureSense = s.io.port('water_low_pressure')
        s.buttRP = s.io.port('RP_water_pump_button')
        s.buttWorkshop = s.io.port('workshop_water_pump_button')

        s.lowPressureSense.subscribe("WaterSupply", s.lowPressureHandler, 1)
        s.buttWorkshop.subscribe("WaterSupply", s.buttPressedHandler, 1)
        s.buttRP.subscribe("WaterSupply", s.buttPressedHandler, 1)

        s.pumpPort.subscribe("WaterSupply", lambda state: s.uiUpdater.call())
        s.lowPressureSense.subscribe("WaterSupply", lambda state: s.uiUpdater.call())

        s.storage = Storage('water_supply.json')
        s._enableAutomatic = s.storage.key('/automatic', True)
        s._isBlocked = s.storage.key('/blocked', False)

        s.uiUpdater = s.skynet.ui.periodicNotifier.register("water_supply", s.uiUpdateHandler, 2000)



    def uiUpdateHandler(s):
        data = {}
        try:
            data['waterPumpEnabled'] = s.pumpPort.cachedState()
        except IoPortCachedStateExpiredError:
            pass

        try:
            data['watersupplyLowPressure'] = s.lowPressureSense.cachedState()
        except IoPortCachedStateExpiredError:
            pass

        data['watersupplyPumpIsLocked'] = s.isBlocked()
        data['watersupplyAutomaticEnabled'] = s._enableAutomatic.val
        s.skynet.emitEvent('water_supply', 'statusUpdate', data)


    def unlock(s):
        s._isBlocked.set(False)


    def lock(s):
        s._isBlocked.set(True)
        if s._timeoutTask:
            s._timeoutTask.remove()
        s.pumpStop()


    def isBlocked(s):
            return s._isBlocked.val


    def pumpRun(s):
        if s.isBlocked():
            raise PumpIsBlockedError(s.log, "Can't run pump. Pump is blocked")

        s.restartAutoStop()
        s.pumpPort.up()


    def restartAutoStop(s):
        t = None
        with s._lock:
            if s._timeoutTask:
                s._timeoutTask.remove()

        t = Task.setTimeout("waterPumpTimeout",
                            int(s.conf['pump_run_timeout']) * 1000, s.pumpStop)

        with s._lock:
            s._timeoutTask = t


    def pumpStop(s):
        s.pumpPort.down()
        with s._lock:
            if s._timeoutTask:
                s._timeoutTask.remove()
                s._timeoutTask = None


    def isStarted(s):
        return s.pumpPort.cachedState()


    def buttPressedHandler(s, state):
        if s.isStarted():
            s.pumpStop()
        else:
            s.pumpRun()


    def lowPressureHandler(s, state):
        if not s._enableAutomatic.val:
            return

        s.restartAutoStop()
        s.pumpRun()


    class HttpHandlers():
        def __init__(s, ws):
            s.ws = ws
            s.hs = ws.httpServer
            s.hs.setReqHandler("GET", "/water_supply/pump_on", s.pumpOnHandler)
            s.hs.setReqHandler("GET", "/water_supply/pump_off", s.pumpOffHandler)
            s.hs.setReqHandler("GET", "/water_supply/switch_automatic_control", s.autoControlSwitchHandler)
            s.hs.setReqHandler("GET", "/water_supply/switch_lock_unlock", s.lockUnlockSwitchHandler)


        def pumpOnHandler(s, args, body, attrs, conn):
            try:
                s.ws.pumpRun()
            except AppError as e:
                raise HttpHandlerError("Can't start water pump: %s" % e)


        def pumpOffHandler(s, args, body, attrs, conn):
            try:
                s.ws.pumpStop()
            except AppError as e:
                raise HttpHandlerError("Can't stop water pump: %s" % e)


        def autoControlSwitchHandler(s, args, body, attrs, conn):
            if s.ws._enableAutomatic.val:
                s.ws._enableAutomatic.set(False)
            else:
                s.ws._enableAutomatic.set(True)
            s.ws.uiUpdater.call()


        def lockUnlockSwitchHandler(s, args, body, attrs, conn):
            if s.ws._isBlocked.val:
                s.ws._isBlocked.set(False)
            else:
                s.ws._isBlocked.set(True)
            s.ws.uiUpdater.call()





