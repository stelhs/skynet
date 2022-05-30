import threading
from Exceptions import *
from Syslog import *

class IoPortBase():
    def __init__(s, io, board, mode, pn, pName):
        s.io = io
        s._lock = threading.Lock()
        s.pName = pName
        s._board = board;
        s._mode = mode;
        s._pn = pn;
        s.log = Syslog('Io_port_%s' % pName)
        s.dbw = IoPortBase.Db(s)
        with s._lock:
            s.blocked = s.dbw.isBlocked()


    def name(s):
        return s.pName


    def mode(s):
        return s._mode


    def pn(s):
        return s._pn;


    def board(s):
        return s._board


    def isBlocked(s):
        with s._lock:
            return s.blocked


    def lock(s):
        with s._lock:
            s.blocked = True
        s.dbw.lock()
       # s.io.uiUpdateBlockedPorts(); #TODO


    def unlock(s):
        with s._lock:
            s.blocked = False
        s.dbw.unlock()
       # s.io.uiUpdateBlockedPorts(); //TODO


    def __repr__(s):
        return "p:%s/%s.%s.%s\n" % (s.name(), s.board().name(), s.mode(), s.pn())


    def __str__(s):
        return "%s/%s.%s.%s" % (s.name(), s.board().name(), s.mode(), s.pn())


    class Db():
        def __init__(s, port):
            s.db = port.io.db
            s.port = port


        def isBlocked(s):
            row = s.db.query("select state from blocked_io_ports " \
                             "where port_name = '%s'" % s.port.name())
            if 'state' not in row:
                return True
            return False


        def lock(s):
            s.unlock()
            s.db.insert('blocked_io_ports',
                        {'port_name': s.name(),
                         'type': s.mode(),
                         'state': 0});

        def unlock(s):
            s.db.query('delete from blocked_io_ports where port_name = "%s"' % s.port.name());
