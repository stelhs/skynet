from Exceptions import *
from Syslog import *


class Gates():
    def __init__(s, skynet):
        s.io = skynet.io
        s.tc = skynet.tc
        s.log = Syslog("Gates")
        s.powerPort = s.io.port('gates_power')
        s.closePort = s.io.port('gates_close')
        s.openPort = s.io.port('gates_open')
        s.openPedPort = s.io.port('gates_open_pedestration')
        s.isClosedPort = s.io.port('gates_closed')

        s.io.registerEventSubscriber("Gates", s.buttOpenCloseHandler,
                                     "remote_guard_sleep", 1)
        s.io.registerEventSubscriber("Gates", s.buttOpenCloseHandler,
                                     "gates_op_cl_workshop", 1)
        s.io.registerEventSubscriber("Gates", s.buttOpenClosePedHandler,
                                     "remote_gates_open_close", 1)
        s.io.registerEventSubscriber("Gates", s.senseGatesClosedHandler,
                                     "gates_closed")
        s.lastRemoteButton = 'open'


    def open(s):
        if not s.isPowerEnabled():
            raise GatesNoPowerError(s.log, "Can't open gates. Power is absent")
        s.closePort.down()
        s.openPort.blink(1000, 500, 1)


    def openPed(s):
        if not s.isPowerEnabled():
            raise GatesNoPowerError(s.log, "Can't open gates. Power is absent")
        s.closePort.down()
        s.openPedPort.blink(1000, 500, 1)


    def close(s):
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


    def buttOpenCloseHandler(s, port, state):
        if s.guard.isStarted():
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


    def buttOpenClosePedHandler(s, port, state):
        if s.guard.isStarted():
            return

        s.io.port('guard_lamp').blink(200, 200, 1)

        if s.isClosed():
            return s.openPed()

        s.close()


    def senseGatesClosedHandler(s, port, state):
        if state:
            s.log.info('gates closed')
            s.tc.toAdmin("Ворота закрылись")
            return
        s.log.info('gates opened')
        s.tc.toAdmin("Ворота открылись")





