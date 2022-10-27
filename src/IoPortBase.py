import threading, time
from Exceptions import *
from Syslog import *
from Skynet import *

class IoPortBase():
    def __init__(s, io, board, mode, pn, pName):
        s.io = io
        s.storage = io.storage
        s.pName = pName
        s._board = board;
        s._mode = mode;
        s._pn = int(pn);
        s.log = Syslog('Io_port_%s' % pName)
        s.dbw = IoPortBase.Db(s)
        s._cachedState = None
        s.updatedTime = 0
        s._blocked = s.storage.key('/ports/%s/blocked' % s.name(), False)
        s.subscribers = []


    def name(s):
        return s.pName


    def mode(s):
        return s._mode


    def pn(s):
        return s._pn;


    def board(s):
        return s._board


    def isBlocked(s):
        return s._blocked.val


    def lock(s):
        s._blocked.set(True)
        s.io.uiUpdateLedsBlockedPorts()


    def unlock(s):
        s._blocked.set(False)
        s.io.uiUpdateLedsBlockedPorts()


    def state(s):
        if (time.time() - s.updatedTime) > s.io.conf['cachedInterval']:
            raise IoPortNotAccessible(s.log, 'Cached state of port %s was expired' % s.name())
        return s._cachedState


    def updateCachedState(s, state):
        s.updatedTime = time.time()
        s._cachedState = state
        s._board.updatedTime = s.updatedTime


    def subscribe(s, name, cb, level=None, delayMs=200):
        subscriber = IoPortBase.EventSubscriber(s, name, cb, level, delayMs)
        s.subscribers.append(subscriber)


    def emitEvent(s, state):
        for sb in s.subscribers:
            if not sb.match(state):
                continue
            try:
                sb.cb(state)
            except AppError as e:
                s.tc.toAdmin("Port %s:%d subscriber Error: %s" % (
                             s.name(), state, e))


    def __repr__(s):
        return "IoPort:%s/%s.%s.%s\n" % (s.name(), s.board().name(), s.mode(), s.pn())


    def __str__(s):
        return "%s/%s.%s.%s" % (s.name(), s.board().name(), s.mode(), s.pn())



    class EventSubscriber():
        def __init__(s, port, name, cb, level, delayMs):
            s.matchTime = int(time.time() * 1000)
            s.name = "%s:%s" % (name, str(level))
            s.port = port
            s.level = level
            s.delayMs = delayMs
            s.cb = cb


        def match(s, level):
            now = int(time.time() * 1000)

            if s.matchTime + s.delayMs > now:
                return False
            s.matchTime = now

            if s.level == None:
                return True
            return level == s.level


        def __repr__(s):
            return "IoPort.EventSubscriber:%s" % s.name



    class Db():
        def __init__(s, port):
            s.db = port.io.db
            s.port = port



