import threading
from Syslog import *

class WaterSupply():
    def __init__(s, skynet):
        s.io = skynet.io
        s.tc = skynet.tc
        s._lock = threading.Lock()
        s._timeoutTask = None
        s.pumpTimeout = 30 # minutes

        s.log = Syslog("WaterSupply")
        s.pumpRelay = s.io.port('water_pump')
        s.lowPressureSense = s.io.port('water_low_pressure')
        s.io.registerEventSubscriber("WaterSupply", s.buttPressedHandler,
                                     "RP_water_pump_button", 1)
        s.io.registerEventSubscriber("WaterSupply", s.buttPressedHandler,
                                     "workshop_water_pump_button", 1)
        s.io.registerEventSubscriber("WaterSupply", s.lowPressureHandler,
                                     "water_low_pressure", 1)

    def enable(s):
        with s._lock:
            s._enabled = True


    def disable(s):
        with s._lock:
            s._enabled = False
            if s._timeoutTask:
                s._timeoutTask.remove()
        s.pumpStop()


    def isEnabled(s):
        with s._lock:
            return s._enabled


    def pumpRun(s):
        if not s.isEnabled():
            s.tc.toAdmin("Попытка включить насос водоснабжения при отключенном водоснабжении")

        s.restartAutoStop()
        s.pumpRelay.up()


    def restartAutoStop(s):
        with s._lock:
            if s._timeoutTask:
                s._timeoutTask.remove()
            s._timeoutTask = Task.setTimeout("waterPumpTimeout",
                                             s.pumpTimeout * 60 * 1000, s.pumpStop)


    def pumpStop(s):
        s.pumpRelay.down()
        with s._lock:
            s._timeoutTask = None


    def isStarted(s):
        return s.pumpRelay.state()


    def buttPressedHandler(s, port, state):
        if s.isStarted():
            s.pumpStop()
        else:
            s.pumpRun()


    def lowPressureHandler(s, port, state):
        s.restartAutoStop()
        s.pumpRun()

