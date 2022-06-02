from IoPortBase import *

class IoPortIn(IoPortBase):
    def __init__(s, io, board, pn, pName):
        super().__init__(io, board, 'in', pn, pName)
        s.db = IoPortIn.Db(s)
        with s._lock:
            s._blockedState = s.db.blockedState()


    def state(s, force=False):
        if not force and s.isBlocked():
            return s.blockedState()

        return s.board().inputState(s);


    def blockedState(s):
        with s._lock:
            return s._blockedState


    def setBlockedState(s, state):
        with s._lock:
            s._blockedState = state
        s.db.setBlockedState(state)
        s.io.uiUpdateBlockedPorts()
        #s.io.trigEvent(s, state, True);


    def unlock(s):
        super().unlock()
        s.setBlockedState(0)


    class Db(IoPortBase.Db):
        def __init__(s, port):
            super().__init__(port)


        def blockedState(s):
            row = s.db.query('select state from blocked_io_ports where port_name = "%s"' %
                               s.port.name());
            if 'state' not in row:
                return 0
            return row['state']


        def setBlockedState(s, state):
            s.db.query('update blocked_io_ports set state = %d where port_name = "%s"' % (
                        state, s.port.name()));


