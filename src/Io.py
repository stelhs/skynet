from Exceptions import *
from SubsystemBase import *
from IoBoardMbio import *
from HttpServer import *


class Io(SubsystemBase):
    def __init__(s, conf, httpServer, db):
        super().__init__("io", conf)
        s.db = db
        s.dbw = Io.Db(s, db)
        s.httpHandlers = Io.HttpHandlers(s, httpServer, s.dbw)
        s.registerBoards()


    def registerBoards(s):
        s._boards = []
        try:
            for ioName, ioInfo in s.conf.items():
                if ioInfo['type'] != 'mbio':
                    continue
                board = IoBoardMbio(s, ioName)
                s._boards.append(board)
        except KeyError as e:
            raise IoPortNotFound(s.log,
                    "Configuration for IO failed in field %s" % e) from e


    def listenedEvents(s):
        return ['mbio']


    def eventHandler(s, source, type, data): # TODO
        pass


    def port(s, pName):
        for port in s.ports():
            if port.name() == pName:
                return port
        raise IoBoardPortNotFound(s.log, "Port %s is not registred" % pName)


    def ports(s, mode=None):
        ports = []
        for board in s.boards():
            ports.extend(board.ports(mode))
        return ports


    def boards(s):
        return s._boards


    def board(s, name):
        for board in s._boards:
            if board.name() == name:
                return board
        raise IoBoardNotFound(s.log, "board() failed: IO board '%s' is not registred" % name)


    def __repr__(s):
        inPortList = ["\t%s" % port for port in s.ports('in')]
        outPortList = ["\t%s" % port for port in s.ports('out')]
        str = "List of input ports:\n"
        str += "\n".join(inPortList)
        str += "\n\nList of output ports:\n"
        str += "\n".join(outPortList)
        return str


    def __str__(s):
        return "bla"


    class HttpHandlers():
        def __init__(s, io, httpServer, dbw):
            s.io = io
            s.dbw = dbw
            s.httpServer = httpServer
            s.httpServer.setReqHandler("GET", "/io/port_config", s.config, ['io'])
            s.httpServer.setReqHandler("GET", "/io/out_port_states", s.outPortStates, ['io'])


        def config(s, args, body, attrs, conn):
            try:
                ioName = args['io']
                conf = s.io.conf[ioName]
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



