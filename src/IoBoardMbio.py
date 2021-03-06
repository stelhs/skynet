import requests, simplejson, time
from Exceptions import *
from IoBoardBase import *


class IoBoardMbio(IoBoardBase):
    def __init__(s, io, ioName):
        super().__init__(io, ioName)
        try:
            s.host = s.conf['host']
            s.port = s.conf['port']
        except KeyError as e:
            raise IoBoardConfigureErr(s.log,
                    "Configuration for mbio '%s' error in field %s" % (ioName, e)) from e

        s.log = Syslog('Mbio')
        s.updatedTime = 0
        s.resetMbio()

        for port in s.ports():
            if port.mode() == 'out':
                port._lastState = 0
            try:
                if port.state() == 'not_configured':
                    continue
                state = int(port.state())
                port.updateCachedState(state)
                if port.mode() == 'out':
                    port._lastState = state
            except IoBoardError:
                pass
            except IoBoardPortNotConfiguredError:
                pass


    def send(s, op, args = {}):
        url = "http://%s:%d/%s" % (s.host, s.port, op)
        try:
            r = requests.get(url = url, params = args)
            resp = r.json()
            if resp['status'] != 'ok' and resp['reason']:
                raise IoBoardMbioError(s.log,
                        "Request '%s' to mbio board '%s' return response with error: %s" % (
                                url, s.name(), resp['reason']))
            return resp
        except requests.RequestException as e:
            raise IoBoardMbioError(s.log,
                    "Request '%s' to mbio board '%s' fails: %s" % (
                            url, s.name(), e)) from e
        except simplejson.errors.JSONDecodeError as e:
            raise IoBoardMbioError(s.log,
                    "Response for '%s' from mbio '%s' parse error: %s. Response: %s" % (
                            url, s.name(), e, r.content)) from e
        except KeyError as e:
            raise IoBoardMbioError(s.log,
                    "Request '%s' to mbio board '%s' return incorrect json: %s" % (
                            url, s.name(), r.content)) from e


    def outputSetState(s, port, state):
        if s.emulator:
            return s.emulator.outputSet(port, state)
        s.send('io/output_set', {'pn': port.pn(), 'state': state})


    def outputState(s, port):
        if s.emulator:
            return s.emulator.outputState(port)
        try:
            ret = s.send('io/output_get', {'pn': port.pn()})
            if ret['state'] == 'not_configured':
                raise IoBoardPortNotConfiguredError(s.log, "Port %s is not configured" % port.name())
            return ret['state']
        except KeyError as e:
            raise IoBoardMbioError(s.log,
                    "Request 'output_get' to mbio board '%s' return json w/o state field: %s" % (
                            s.name(), ret))


    def inputState(s, port):
        if s.emulator:
            return s.emulator.inputState(port)
        try:
            ret = s.send('io/input_get', {'pn': port.pn()})
            return ret['state']
        except KeyError as e:
            raise IoBoardMbioError(s.log,
                    "Request 'input_get' to mbio board '%s' return json w/o state field: %s" % (
                            s.name(), ret))


    def setBlink(s, port, d1, d2=0, number=1):
        if s.emulator:
            return s.emulator.outputSet(port, 'blink %d %d %d' % (d1, d2, number))
        s.send("io/output_set", {'pn': port.pn(),
                              'state': 'blink',
                              'd1': d1,
                              'd2': d2,
                              'number': number});

    def batteryInfo(s):
        try:
            ret = s.send('battery')
            return ret['data']
        except KeyError as e:
            raise IoBoardMbioError(s.log,
                    "Request 'batteryInfo'return json w/o 'data' field: %s" % ret)


    def resetMbio(s):
        try:
            s.send('reset')
        except IoBoardError:
            pass


    def updateCachedState(s, portStateList):
        s.updatedTime = int(time.time())
        for row in portStateList:
            port = s.io.port(row['port_name'])
            port.updateCachedState(row['state'])

