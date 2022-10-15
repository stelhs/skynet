from Exceptions import *
from IoBoardMbio import *
from HttpServer import *
from Syslog import *
from SkynetStorage import *


class Io():
    def __init__(s, skynet):
        s.skynet = skynet
        s.conf = skynet.conf.io
        s.httpServer = skynet.httpServer
        s.db = skynet.db
        s.tc = skynet.tc

        s.log = Syslog('Io')
        s.storage = SkynetStorage(skynet, 'io.json')

        s.httpHandlers = Io.HttpHandlers(s)
        s.registerBoards()
        s.skynet = skynet
        s.skynet.registerEventSubscriber('Io', s.eventHandler, ('mbio', ), ('portTriggered', ))
        s.skynet.registerEventSubscriber('Io', s.boardStatusHandler, ('mbio', ), ('portsStates', ))
        s.chechTask = Task.setPeriodic('IoCheckTask', 30000, s.checkBoards)


    def toAdmin(s, msg):
        s.tc.toAdmin("Io: %s" % msg)


    def boardStatusHandler(s, source, type, data):
        board = s.board(data['io_name'])
        board.updateCachedState(data['ports'])
        s.skynet.emitEvent('io', 'portsStates', data)


    def eventHandler(s, source, type, data):
        try:
            pn = int(data['pn'])
            state = int(data['state'])
            bName = data['io_name']
            board = s.board(bName)
            port = board.portByPn(pn)
        except KeyError as e:
            s.toAdmin("IO event handler error: field %s is absent in 'portTriggered' evType" % e)
            return
        except IoError as e:
            s.toAdmin("IO event handler error: board '%s' send event for " \
                         "pn:%d, state:%d but it can't be processing: %s" % (bName, pn, state, e))
            return

        if port.isBlocked():
            return

        try:
            port.updateCachedState(state)
            s.emitEvent(port, state)
        except AppError as e:
            s.toAdmin("IO event handler %s error: %s" % (port, e))


    def emitEvent(s, port, state):
        port.emitEvent(state)
        try:
            s.db.insert('io_events',
                        {'mode': port.mode(),
                         'port_name': port.name(),
                         'io_name': port.board().name(),
                         'port': port.pn(),
                         'state': state});
        except DatabaseConnectorError as e:
            pass


    def registerBoards(s):
        s._boards = []
        try:
            for ioName, ioInfo in s.conf['boards'].items():
                if ioInfo['type'] != 'mbio':
                    continue
                board = IoBoardMbio(s, ioName)
                s._boards.append(board)
        except KeyError as e:
            raise IoPortNotFound(s.log,
                    "Configuration for IO failed in field %s" % e) from e

        for board in s.boards():
            board.init()


    def port(s, pName):
        for port in s.ports():
            if port.name() == pName:
                return port
        raise IoBoardPortNotFound(s.log, "Port %s is not registred" % pName)


    def ports(s, mode=None, blocked=None):
        ports = []
        for board in s.boards():
            ports.extend(board.ports(mode, blocked))
        return ports


    def boards(s):
        return s._boards


    def board(s, name):
        for board in s._boards:
            if board.name() == name:
                return board
        raise IoBoardNotFound(s.log, "board() failed: IO board '%s' is not registred" % name)


    def uiUpdateBlockedPorts(s):
        listIn = [{'state': int(p.blockedState()), 'type': p.mode(),
                   'port_name': p.name(), 'isBlocked': p.isBlocked()}
                   for p in s.ports(mode='in')]
        listOut = [{'state': 0, 'type': p.mode(),
                    'port_name': p.name()} for p in s.ports(mode='out', blocked=True)]
        list = listIn
        list.extend(listOut)
        s.skynet.emitEvent('io', 'boardsBlokedPortsList', list)


    def checkBoards(s, task):
        now = int(time.time())
        for board in s.boards():
            if (now - board.updatedTime) > 5:
                s.log.err('Board %s is absent' % board.name())
                s.toAdmin('Плата %s недоступна' % board.name())



    def destroy(s):
        print("destroy Io")
        s.storage.destroy()


    def __repr__(s):
        inPortList = ["\t%s" % port for port in s.ports('in')]
        outPortList = ["\t%s" % port for port in s.ports('out')]
        str = "List of input ports:\n"
        str += "\n".join(inPortList)
        str += "\n\nList of output ports:\n"
        str += "\n".join(outPortList)
        return str



    class HttpHandlers():
        def __init__(s, io):
            s.io = io
            s.skynet = io.skynet
            s.hs = s.skynet.httpServer
            s.hs.setReqHandler("GET", "/io/port_config", s.config, ('io',))
            s.hs.setReqHandler("GET", "/io/out_port_states", s.outPortStates, ('io',))

            s.regUiHandler('r', "GET", "/io/request_io_blocked_ports", s.requestIoBlockedPorts)
            s.regUiHandler('w', "GET", "/io/port/toggle_lock_unlock", s.portLockUnlock, ('port_name',))
            s.regUiHandler('w', "GET", "/io/port/toggle_blocked_state", s.portBlockedState, ('port_name',))
            s.regUiHandler('w', "GET", "/io/port/toggle_out_state", s.portToggleOutState, ('port_name',))
            s.regUiHandler('w', "GET", "/io/port/blink", s.portSetBlink, ('port_name', 'd1', 'd2', 'number'))


        def regUiHandler(s, permissionMode, method, url, handler,
                                requiredFields=[], retJson=True):
            s.skynet.ui.setReqHandler('io', permissionMode, method,
                                      url, handler, requiredFields, retJson)


        def config(s, args, conn):
            try:
                ioName = args['io']
                conf = s.io.conf['boards'][ioName]
            except KeyError:
                raise HttpHandlerError("board '%s' is not registred" % ioName)
            return {'config': conf}


        def outPortStates(s, args, conn):
            ioName = args['io']
            try:
                board = s.io.board(ioName)
                ports = board.ports()
            except IoBoardNotFound:
                raise HttpHandlerError("Io board '%s' is not registred" % ioName)

            try:
                listStates = [{'pn': port.pn(),
                               'state': port.lastState()} for port in ports \
                              if port.mode() == 'out' and port.lastState() != None]
                return {'listStates': listStates}
            except DatabaseConnectorError as e:
                raise HttpHandlerError('Database error: %s' % e)


        def requestIoBlockedPorts(s, args, conn):
            s.io.uiUpdateBlockedPorts()


        def portLockUnlock(s, args, conn):
            portName = args['port_name']
            try:
                port = s.io.port(portName)
                if port.isBlocked():
                    port.unlock()
                else:
                    port.lock()
                    if port.mode() == 'in':
                        port.setBlockedState(port.blockedState())
            except AppError as e:
                raise HttpHandlerError("Can't toggle Lock/Unlock port %s: %s" % (portName ,e))


        def portBlockedState(s, args, conn):
            portName = args['port_name']
            try:
                port = s.io.port(portName)
                if port.mode() != 'in':
                    raise HttpHandlerError("Can't change blocked state for '%s' port" % port.mode())

                if port.blockedState():
                    port.setBlockedState(0)
                else:
                    port.setBlockedState(1)
            except AppError as e:
                raise HttpHandlerError("Can't change blocked state for 'in' port %s: %s" % (portName, e))


        def portToggleOutState(s, args, conn):
            portName = args['port_name']
            try:
                port = s.io.port(portName)
                if port.mode() != 'out':
                    raise HttpHandlerError("Can't change output state for '%s' port" % port.mode())

                if port.state():
                    port.down(force=True)
                else:
                    port.up(force=True)
            except AppError as e:
                raise HttpHandlerError("Can't change output state for 'out' port %s: %s" % (portName, e))


        def portSetBlink(s, args, conn):
            portName = args['port_name']
            d1 = args['d1']
            d2 = args['d2']
            number = args['number']
            try:
                port = s.io.port(portName)
                if port.mode() != 'out':
                    raise HttpHandlerError("Can't set blink for '%s' port" % port.mode())

                port.blink(d1, d2, number)
            except AppError as e:
                raise HttpHandlerError("Can't set blink for 'out' port %s: %s" % (portName, e))



