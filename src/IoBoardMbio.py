import time
from Exceptions import *
from IoBoardBase import *
from HttpClient import *


class IoBoardMbio(IoBoardBase):
    def __init__(s, io, ioName):
        super().__init__(io, ioName)
        try:
            s.host = s.conf['host']
            s.port = s.conf['port']
        except KeyError as e:
            raise IoBoardConfigureErr(s.log,
                    "Configuration for mbio '%s' error in field %s" % (ioName, e)) from e

        s.httpClient = HttpClient(ioName, s.host, s.port)
        s.log = Syslog('Mbio')


    def send(s, op, args = {}):
        try:
            return s.httpClient.reqGet(op, args)
        except HttpClient.Error as e:
            raise IoBoardMbioError(s.log, e) from e


    def outputSetState(s, port, state):
        if s.emulator:
            return s.emulator.outputSet(port, state)

        if (time.time() - s.updatedTime) > s.io.conf['cachedInterval']:
            raise IoBoardNotAccessible(s.log, 'mbio board %s is not accessible' % s.name())

        s.send('io/output_set', {'pn': port.pn(), 'state': state})


    def portSyncState(s, port):
        if s.emulator:
            if port.mode() == 'in':
                return s.emulator.inputState(port)
            return s.emulator.outputState(port)

        try:
            ret = s.send('io/sync_state', {'pn': port.pn()})
            if ret['state'] == 'not_configured':
                raise IoBoardPortNotConfiguredError(s.log, "Port %s is not configured" % port.name())
            return ret['state']
        except KeyError as e:
            raise IoBoardMbioError(s.log,
                    "Request 'sync_state' to mbio board '%s' return json w/o state field: %s" % (
                            s.name(), ret))


    def setBlink(s, port, d1, d2=0, number=1):
        if s.emulator:
            return s.emulator.outputSet(port, 'blink %d %d %d' % (d1, d2, number))

        if (time.time() - s.updatedTime) > s.io.conf['cachedInterval']:
            raise IoBoardNotAccessible(s.log, 'mbio board %s is not accessible' % s.name())

        s.send("io/output_set", {'pn': port.pn(),
                              'state': 'blink',
                              'd1': d1,
                              'd2': d2,
                              'number': number});

    def batteryInfo(s):
        if (time.time() - s.updatedTime) > s.io.conf['cachedInterval']:
            raise IoBoardNotAccessible(s.log, 'mbio board %s is not accessible' % s.name())

        try:
            ret = s.send('battery')
            return ret['data']
        except KeyError as e:
            raise IoBoardMbioError(s.log,
                    "Request 'batteryInfo'return json w/o 'data' field: %s" % ret)


    def setZeroChargerCurrents(s):
        if (time.time() - s.updatedTime) > s.io.conf['cachedInterval']:
            raise IoBoardNotAccessible(s.log, 'mbio board %s is not accessible' % s.name())
        s.send('set_zero_charger_current')


    def resetMbio(s):
        try:
            s.send('reset')
        except IoBoardError:
            pass


    def hardReboot(s):
        if not 'rebootPort' in s.conf or not s.conf['rebootPort']:
            raise IoError(s.log, "Reboot is not supported")
        p = s.io.port(s.conf['rebootPort'])
        p.blink(2000, 1000, 1)






