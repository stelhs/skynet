import threading
from Exceptions import *
from Syslog import *
from Skynet import *

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
        s._cachedState = None
        s.updatedTime = 0


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
        s.io.uiUpdateBlockedPorts()


    def unlock(s):
        with s._lock:
            s.blocked = False
        s.dbw.unlock()
        s.io.uiUpdateBlockedPorts()


    def cachedState(s):
        if s.mode() == 'out':
            return s._cachedState

        if (time.time() - s.updatedTime) > s.io.conf['cachedInterval']:
            raise IoPortCachedStateExpiredError(s.log, 'Cached state of port %s was expired' % s.name())
        return s._cachedState


    def updateCachedState(s, state):
        s.updatedTime = time.time()
        s._cachedState = state


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
            if 'state' in row:
                return True
            return False


        def lock(s):
            s.unlock()
            print("db lock")
            s.db.insert('blocked_io_ports',
                        {'port_name': s.port.name(),
                         'type': s.port.mode(),
                         'state': 0});

        def unlock(s):
            s.db.query('delete from blocked_io_ports where port_name = "%s"' % s.port.name());
