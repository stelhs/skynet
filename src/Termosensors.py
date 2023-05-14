import time, threading
from Exceptions import *
from Syslog import *
from Skynet import *


class Termosensors():
    def __init__(s, skynet):
        s.httpServer = skynet.httpServer
        s.conf = skynet.conf.termosensors
        s.skynet = skynet
        s.sensors = []
        s.log = Syslog("Termosensors")

        try:
            for sName, sInfo in s.conf['sensors'].items():
                sensor = Termosensor(s, sName, sInfo['addr'],
                                     sInfo['description'],
                                     sInfo['ioBoard'],
                                     sInfo['min'],
                                     sInfo['max'])
                s.sensors.append(sensor)
        except KeyError as e:
            raise TermosensorConfiguringError(s.log,
                    "Configuration error: field %s is absent" % e) from e

        s.httpHandlers = Termosensors.HttpHandlers(s, s.httpServer)
        skynet.registerEventSubscriber('TermosensorsMbio', s.eventHandlerMbio,
                                        ('mbio', ), ('termoStates', ))
        skynet.registerEventSubscriber('TermosensorsBoiler', s.eventHandlerBoiler,
                                        ('boiler', ), ('boilerState', ))


    def eventHandlerMbio(s, source, type, data):
        try:
            for addr, t in data['termosensors'].items():
                try:
                    sensor = s.sensorByAddr(addr)
                    sensor.update(t)
                except TermosensorNotRegistredError:
                    pass
        except KeyError as e:
            raise EventHandlerError(s.log,
                    "eventHandler mbio failed: field %s is absent in event data" % e) from e
        s.updateUi()


    def eventHandlerBoiler(s, source, type, data):
        if 'room_t' in data:
            s.sensor('workshop_inside1').update(data['room_t'])
        if 'boiler_t' in data:
            s.sensor('boiler_inside').update(data['boiler_t'])
        if 'boiler_box_t' in data:
            s.sensor('boiler_inside_case').update(data['boiler_box_t'])
        if 'return_t' in data:
            s.sensor('workshop_radiators').update(data['return_t'])
        s.updateUi()


    def sensor(s, name):
        for sensor in s.sensors:
            if sensor.name() == name:
                return sensor
        raise TermosensorNotRegistredError(s.log,
                "sensor() failed: sensor name '%s' is not registred" % name)


    def sensorByAddr(s, addr):
        for sensor in s.sensors:
            if sensor.addr() == addr:
                return sensor
        raise TermosensorNotRegistredError(s.log,
                "sensor() failed: sensor addr '%s' is not registred" % addr)


    def updateUi(s):
        data = {}
        for sensor in s.sensors:
            try:
                data["ssTermosensor_%s" % sensor.name()] = round(sensor.t(), 1)
            except TermosensorNoDataError:
                pass
        s.skynet.emitEvent('termosensors', 'sevenSegsUpdate', data)


    def textStat(s):
        text = "Датчики температуры:\n"
        for sn in s.sensors:
            try:
                text += "    %s: %.1f°\n" % (sn.description(), sn.t())
            except AppError as e:
                pass
        return text


    def __repr__(s):
        text = "Termosensors:\n"
        for sn in s.sensors:
            text += "\t%s: %.2f\n" % (sn.name(), sn.t())
        return text


    class HttpHandlers():
        def __init__(s, ts, httpServer):
            s.ts = ts
            s.httpServer = httpServer
            s.httpServer.setReqHandler("GET", "/io/termosensor_config", s.termosensor, ['io'])


        def termosensor(s, args, conn):
            ioBoardName = args['io']
            return {'list' :[{'addr': sn.addr(), 'min': sn.minT(), 'max': sn.maxT()} \
                             for sn in s.ts.sensors if sn.ioBoardName() == ioBoardName]}




class Termosensor():
    def __init__(s, manager, name, addr, description, ioName, minT, maxT):
        s.manager = manager
        s.conf = manager.conf
        s.log = Syslog('Termosensor_%s' % name)
        s._name = name
        s._addr = addr
        s._description = description
        s._ioName = ioName
        s._minT = minT
        s._maxT = maxT
        s._subscribers = []
        s.updateTime = 0


    def update(s, t):
        if not t or t == 'None':
            return
        s._t = float(t)
        s.updateTime = int(time.time())
        if len(s._subscribers):
            for sb in s._subscribers:
                sb.cb(s._t)


    def t(s):
        now = int(time.time())
        if (now - s.updateTime) > s.conf['cachedInterval']:
            raise TermosensorNoDataError(s.log,
                    "termosensor is not updated more then %d seconds" % s.conf['cachedInterval'])
        return s._t


    def name(s):
        return s._name


    def ioBoardName(s):
        return s._ioName


    def description(s):
        return s._description


    def addr(s):
        return s._addr


    def minT(s):
        return s._minT


    def maxT(s):
        return s._maxT


    def registerSubscriber(s, name, cb):
        s._subscribers.append(Termosensor.Subscriber(name, cb))


    def __str__(s):
        return "Termosensor:%s" % s.name()


    def __repr__(s):
        return "Termosensor:%s\n" % s.name()



    class Subscriber():
        def __init__(s, name, cb):
            s.name = name
            s.cb = cb

        def __repr__(s):
            return "Termosensor.Subscriber:%s" % s.name()


        def __str__(s):
            return "Termosensor.Subscriber:%s" % s.name()



