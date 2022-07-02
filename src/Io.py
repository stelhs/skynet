from Exceptions import *
from IoBoardMbio import *
from HttpServer import *
from Syslog import *


class Io():
    def __init__(s, skynet):
        s.log = Syslog('Io')
        s.conf = skynet.conf.io
        s.httpServer = skynet.httpServer
        s.db = skynet.db
        s.tc = skynet.tc
        s.storage = Storage('io.json')

        s.dbw = Io.Db(s, s.db)
        s.httpHandlers = Io.HttpHandlers(s, s.httpServer, s.dbw)
        s.registerBoards()
        s.skynet = skynet
        s.skynet.registerEventSubscriber('Io', s.eventHandler, ('mbio', ), ('portTriggered', ))
        s.skynet.registerEventSubscriber('Io', s.boardStatusHandler, ('mbio', ), ('portsStates', ))


    def boardStatusHandler(s, source, type, data):
        for row in data['ports']:
            port = s.port(row['port_name'])
            port.updateCachedState(row['state'])

        s.skynet.emitEvent('io', 'portsStates', data)


    def eventHandler(s, source, type, data):
        try:
            pn = int(data['pn'])
            state = int(data['state'])
            bName = data['io_name']
            board = s.board(bName)
            port = board.portByPn(pn)
        except KeyError as e:
            s.tc.toAdmin("IO event handler error: field %s is absent in 'portTriggered' evType" % e)
            return
        except IoError as e:
            s.tc.toAdmin("IO event handler error: board '%s' send event for " \
                         "pn:%d, state:%d but it can't be processing: %s" % (bName, pn, state, e))
            return

        if port.isBlocked():
            return

        try:
            port.updateCachedState(state)
            s.emitEvent(port.name(), state)
        except AppError as e:
            s.tc.toAdmin("IO event handler %s error: %s" % (port, e))


    def emitEvent(s, portName, state):
        port = s.port(portName)
        port.emitEvent(state)


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


    def __repr__(s):
        inPortList = ["\t%s" % port for port in s.ports('in')]
        outPortList = ["\t%s" % port for port in s.ports('out')]
        str = "List of input ports:\n"
        str += "\n".join(inPortList)
        str += "\n\nList of output ports:\n"
        str += "\n".join(outPortList)
        return str



    class HttpHandlers():
        def __init__(s, io, httpServer, dbw):
            s.io = io
            s.dbw = dbw
            s.hs = httpServer
            s.hs.setReqHandler("GET", "/io/port_config", s.config, ('io',))
            s.hs.setReqHandler("GET", "/io/out_port_states", s.outPortStates, ('io',))
            s.hs.setReqHandler("GET", "/io/request_io_blocked_ports", s.requestIoBlockedPorts)
            s.hs.setReqHandler("GET", "/io/port/toggle_lock_unlock", s.portLockUnlock, ('port_name',))
            s.hs.setReqHandler("GET", "/io/port/toggle_blocked_state", s.portBlockedState, ('port_name',))
            s.hs.setReqHandler("GET", "/io/port/toggle_out_state", s.portToggleOutState, ('port_name',))
            s.hs.setReqHandler("GET", "/io/port/blink", s.portSetBlink, ('port_name', 'd1', 'd2', 'number'))


        def config(s, args, body, attrs, conn):
            try:
                ioName = args['io']
                conf = s.io.conf['boards'][ioName]
            except KeyError:
                raise HttpHandlerError("board '%s' is not registred" % ioName)
            return {'config': conf}


        def outPortStates(s, args, body, attrs, conn):
            ioName = args['io']
            try:
                s.io.board(ioName)
            except IoBoardNotFound:
                raise HttpHandlerError("Io board '%s' is not registred" % ioName)

            try:
                ports = s.dbw.loadLastOutputState(ioName)
                return {'ports': ports}
            except DatabaseConnectorError as e:
                raise HttpHandlerError('Database error: %s' % e)


        def requestIoBlockedPorts(s, args, body, attrs, conn):
            s.io.uiUpdateBlockedPorts()


        def portLockUnlock(s, args, body, attrs, conn):
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


        def portBlockedState(s, args, body, attrs, conn):
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


        def portToggleOutState(s, args, body, attrs, conn):
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


        def portSetBlink(s, args, body, attrs, conn):
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


    class Db():
        def __init__(s, io, db):
            s.io = io
            s.db = db


        def loadLastOutputState(s, ioName):
            query = "SELECT io_events.io_name, " \
                            "io_events.port, " \
                            "io_events.port_name, " \
                            "io_events.state " \
                    "FROM io_events " \
                    "INNER JOIN " \
                        '( SELECT io_name, port_name, max(id) as last_id ' \
                         'FROM io_events ' \
                         'GROUP BY io_name, port_name ) as b ' \
                     'ON io_events.port_name = b.port_name AND ' \
                        'io_events.io_name = b.io_name AND ' \
                        'io_events.id = b.last_id ' \
                     "WHERE io_events.io_name = '%s' " \
                     'ORDER BY io_events.io_name, io_events.port_name' % ioName
            return s.db.queryList(query)



