from IoPortBase import *

class IoPortIn(IoPortBase):
    def __init__(s, io, board, pn, pName):
        super().__init__(io, board, 'in', pn, pName)
        s._blockedState = s.storage.key('/ports/%s/blockedState' % s.name(), False)


    def blockedState(s):
        return s._blockedState.val


    def setBlockedState(s, state):
        s._blockedState.set(state)
        s.io.uiUpdateLedsBlockedPorts()
        if s.isBlocked():
            s.updateCachedState(state)
            s.io.emitEvent(s, state)


    def state(s, force=False):
        if not force and s.isBlocked():
            return s.blockedState()
        return super().state()


    def unlock(s):
        super().unlock()



