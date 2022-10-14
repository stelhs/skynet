from IoPortBase import *

class IoPortOut(IoPortBase):
    def __init__(s, io, board, pn, pName):
        super().__init__(io, board, 'out', pn, pName)
        s.log = Syslog('IoOutPort')
        s.db = io.skynet.db
        s._lastState = None


    def up(s, force=False):
        if s.isBlocked() and not force:
            raise IoPortBlockedError(s.log, "port is blocked, set state to '1' was ignored")
        s.setState(1)


    def down(s, force=False):
        if s.isBlocked() and not force:
            raise IoPortBlockedError(s.log, "port is blocked, set state to '0' was ignored")
        s.setState(0)


    def setState(s, state):
        s._lastState = state
        s.board().outputSetState(s, state)
        s.updateCachedState(state)

        try:
            s.db.insert('io_events',
                        {'mode': 'out',
                         'port_name': s.name(),
                         'io_name': s.board().name(),
                         'port': s.pn(),
                         'state': state});
        except DatabaseConnectorError as e:
            pass

        s.io.emitEvent(s.name(), state)


    def lastState(s):
        if s._lastState == None:
            raise IoBoardPortNoLastStateError(s.log, "port %s Last state is absent" % s.name())
        return s._lastState


    def blink(s, d1, d2=0, number=1):
        s.board().setBlink(s, d1, d2, number)


    def state(s):
        return s.board().outputState(s);



