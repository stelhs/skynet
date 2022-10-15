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
        s.conf = s.io.conf['boards'][ioName]
        s.updatedTime = 0

        s._ports = []

        try:
            for pn, pInfo in s.conf['in'].items():
                pName = pInfo['name']
                s._ports.append(IoPortIn(s.io, s, pn, pName))

            for pn, pName in s.conf['out'].items():
                s._ports.append(IoPortOut(s.io, s, pn, pName))
        except KeyError as e:
            raise IoBoardConfigureErr(s.log,
                    "Configuration for board IO '%s' error in field %s" % (ioName, e)) from e


        s.emulator = None
        if s.conf['emulate']:
            s.emulator = IoBoardBase.Emulator(s)


    def init(s):
        if s.emulator:
            s.emulator.init()


    def name(s):
        return s.ioName;


    def setBlink(s, port, d1, d2=0, number=0):
        raise NotImplementedError


    def outputSet(s, port, state):
        if s.emulator:
            s.emulator.outputSet(port, state)
            return


    def port(pName):
        for port in s._ports:
            if port.name() == pName:
                return port
        raise IoBoardPortNotFound(s.log, "port %s not registred" % pName)


    def portByPn(s, pn):
        for port in s._ports:
            if port.pn() == pn:
                return port
        raise IoBoardPortNotFound(s.log, "port pn:%d not registred" % pn)


    def ports(s, mode=None, blocked=None):
        list = []
        for port in s._ports:
            if mode and port.mode() != mode:
                continue

            if blocked and port.isBlocked() != blocked:
                continue
            list.append(port)
        return list


    def __repr__(s):
        return "b:%s" % s.name()


    def __str__(s):
        return "Board %s" % s.name()


    def updateCachedState(s, portStateList):
        s.updatedTime = int(time.time())
        for row in portStateList:
            port = s.io.port(row['port_name'])
            port.updateCachedState(row['state'])



    class Emulator:
        def __init__(s, board):
            s.inputs = {}
            s.outputs = {}
            s.log = Syslog('IoBoardBase.Emulator')
            s.conf = board.conf
            s.board = board
            s.outputFileName = '%s_fake_out_ports' % s.board.name()
            s.inputFileName = '%s_fake_in_ports' % s.board.name()

            try:
                for pn, pInfo in s.conf['in'].items():
                    print("IN pInfo = %s" % pInfo)
                    pName = pInfo['name']
                    s.inputs[pName] = 0

                for pn, pName in s.conf['out'].items():
                    s.outputs[pName] = 0
            except Exception as e:
                raise IoBoardEmulatorError(s.log, 'IO configuration error: %s' % e) from e

            s.loadInputs()
            s.loadOutputs()


        def init(s):
            s.updater = s.board.io.skynet.periodicNotifier.register(
                            "mbio_%s_emulator", s.updateHandler, 2000)


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
                              "file %s parse error on line %d: %s" % (fName, cnt, e)) from e

                state = key.strip()
                pName = val.strip()
                try:
                    list[pName] = int(state)
                except ValueError:
                    list[pName] = 0
            return list


        def save(s, fName, list):
            str = ""
            sep = ""
            for pName, state in list.items():
                str += "%s%s: %s" % (sep, state, pName)
                sep = "\n"
            filePutContent(fName, str)


        def loadInputs(s):
            try:
                s.inputs.update(s.parse(s.inputFileName))
            except FileError as e:
                s.save(s.inputFileName, s.inputs)


        def loadOutputs(s):
            try:
                s.outputs.update(s.parse(s.outputFileName))
            except FileError as e:
                s.save(s.outputFileName, s.outputs)


        def outputSet(s, port, state):
            s.outputs[port.name()] = state
            s.save(s.outputFileName, s.outputs)


        def updateHandler(s):
            ports = []
            for port in s.board.ports():
                if not port.name():
                    continue

                try:
                    state = port.state()
                    info = {'port_name': port.name(),
                            'type': port.mode(),
                            'state': port.state()}
                except IoError:
                    continue
                ports.append(info)

            data = {'io_name': s.board.name(), 'ports': ports}
            s.board.io.boardStatusHandler('mbio', 'portsStates', data)


