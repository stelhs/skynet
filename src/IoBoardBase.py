import os
from Exceptions import *
from Io import *
from IoPortIn import *
from IoPortOut import *

class IoBoardBase():
    def __init__(s, io, ioName):
        s.io = io
        s.ioName = ioName
        s.log = Syslog('Board_%s' % ioName)

        s._ports = []

        try:
            for pn, pInfo in s.io.conf[ioName]['in'].items():
                pName = pInfo['name']
                s._ports.append(IoPortIn(s.io, s, pn, pName))

            for pn, pName in s.io.conf[ioName]['out'].items():
                s._ports.append(IoPortOut(s.io, s, pn, pName))
        except KeyError as e:
            raise IoBoardConfigureErr(s.log,
                    "Configuration for board IO '%s' error in field %s" % (ioName, e)) from e

        s.emulator = None
        if os.path.isfile('DISABLE_HW'):
            s.emulator = IoBoardBase.Emulator(s.io)


    def name(s):
        return s.ioName;


    def setBlink(s, port, d1, d2=0, number=0):
        raise NotImplementedError


    def outputSet(s, port, state):
        if s.emulator:
            s.emulator.outputSet(port, state)
            return


    def outputState(s, port):
        if s.emulator:
            return s.emulator.outputState(port)
        return


    def inputState(s, port):
        if s.emulator:
            return s.emulator.outputState(port)


    def port(pName):
        for port in s._ports:
            if port.name() == pName:
                return port
        raise IoBoardPortNotFound("port %s not registred" % pName)


    def ports(s, mode=None):
        list = []
        for port in s._ports:
            if mode:
                if port.mode() == mode:
                    list.append(port)
                continue
            list.append(port)
        return list


    def trigAllPorts(s):
        for port in s._ports('in'):
            state = port.state();
            s.io.emitEvent(port, state)


    def __repr__(s):
        return "b:%s" % s.name()


    def __str__(s):
        return "Board %s" % s.name()



    class Emulator:
        def __init__(s, io):
            s.inputs = {}
            s.outputs = {}
            s.log = Syslog('IoBoardBase.Emulator')

            try:
                for ioName, ioInfo in s.io.conf.items():
                    for pn, pInfo in ioInfo['in'].items():
                        pName = pInfo['name']
                        s.inputs[pName] = 0

                    for pn, pInfo in ioInfo['out'].items():
                        pName = pInfo['name']
                        s.outputs[pName] = 0
            except Exception as e:
                raise IoBoardEmulatorError(s.log, 'IO configuration error: %s' % e) from e

            s.loadInputs()
            s.loadOutputs()


        def parse(s, fName):
            list = {}
            c = fileGetContent(fName)

            cnt = 1
            for line in c.split("\n"):
                try:
                    key, val = line.split(':')
                    cnt += 1
                except ValueError as e:
                    raise IoBoardEmulatorError(s.log,
                              "file %s parse error on line %d: %e" % (fName, cnt, e)) from e

                state = key.strip()
                pName = val.strip()
                list[pName] = state
            return list


        def save(s, fName, list):
            str = ""
            for pName, state in list.items():
                str += "%d: %s" % (state, pName)
            filePutContent(fName, str)


        def loadInputs(s):
            try:
                s.inputs.update(s.parse('fake_in_ports'))
            except FileContentEx as e:
                s.save('fake_in_ports', s.inputs)


        def loadOutputs(s):
            try:
                s.outputs.update(s.parse('fake_out_ports'))
            except FileContentEx as e:
                s.save('fake_out_ports', s.outputs)


        def outputSet(s, port, state):
            s.outputs[port.name()] = state
            s.save()


        def outputState(s, port):
            return s.outputs[port.name()]


        def inputState(s, port):
            return s.inputs[port.name()]

