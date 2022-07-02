from IoPortBase import *

class IoPortIn(IoPortBase):
    def __init__(s, io, board, pn, pName):
        super().__init__(io, board, 'in', pn, pName)
        s._blockedState = s.storage.key('/ports/%s/blockedState' % s.name(), False)


    def state(s, force=False):
        if not force and s.isBlocked():
            return s.blockedState()

        return s.board().inputState(s);


    def blockedState(s):
        return s._blockedState.val


    def setBlockedState(s, state):
        s._blockedState.set(state)
        s.io.uiUpdateBlockedPorts()
        if s.isBlocked():
            s.updateCachedState(state)
            s.io.emitEvent(s.name(), state)


    def cachedState(s):
        if s.isBlocked():
            return s.blockedState()
        return super().cachedState()


    def unlock(s):
        super().unlock()



