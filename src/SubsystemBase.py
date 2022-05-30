from Syslog import *

class SubsystemBase:
    def __init__(s, name, conf):
        s.log = Syslog('Subsystem_%s' % name)
        s.conf = conf
        s._name = name


    def listenedEvents(s):
        raise NotImplementedError("subsystem %s:  listenedEvents() is not implemented" % s.name())


    def eventHandler(s, source, type, data):
        raise NotImplementedError("subsystem %s:  eventHandler() is not implemented" % s.name())


    def name(s):
        return s._name