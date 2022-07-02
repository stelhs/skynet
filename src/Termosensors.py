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

        try:
            for sName, sInfo in s.conf['sensors'].items():
                sensor = Termosensor(s, sName, sInfo['addr'],
                                     sInfo['description'],
                                     sInfo['ioBoard'])
                s.sensors.append(sensor)
        except KeyError as e:
            raise TermosensorConfiguringError(s.log,
                    "Configuration error: field %s is absent" % e) from e

        s.httpHandlers = Termosensors.HttpHandlers(s, s.httpServer)
        skynet.registerEventSubscriber('TermosensorsMbio', s.eventHandlerMbio,
                                        ('mbio', ), ('termoStates', ))
        skynet.registerEventSubscriber('TermosensorsBoiler', s.eventHandlerBoiler,
                                        ('boiler', ), ('boilerStatus', ))


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
                    "eventHandler of '%s' failed: field %s is absent in event data" % (s.name(), e)) from e
        s.updateUi()


    def eventHandlerBoiler(s, source, type, data):
        try:
            s.sensor('workshop_inside1').update(data['room_t'])
            s.sensor('boiler_inside').update(data['boiler_t'])
            s.sensor('boiler_inside_case').update(data['boiler_box_t'])
            s.sensor('workshop_radiators').update(data['return_t'])
        except KeyError as e:
            raise EventHandlerError(s.log,
                    "eventHandler of '%s' failed: field %s is absent in event data" % (s.name(), e)) from e
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
                data[sensor.name()] = sensor.t()
            except TermosensorNoDataError:
                pass
        s.skynet.emitEvent('termosensors', 'termosensorsUpdate', data)


    class HttpHandlers():
        def __init__(s, ts, httpServer):
            s.ts = ts
            s.httpServer = httpServer
            s.httpServer.setReqHandler("GET", "/io/termosensor_config", s.termosensor, ['io'])


        def termosensor(s, args, body, attrs, conn):
            ioBoardName = args['io']
            list = []
            for sensor in s.ts.sensors:
                if sensor.ioBoardName() != ioBoardName:
                    continue
                if sensor.addr():
                    list.append(sensor.addr())
            return {'list': list}




class Termosensor():
    def __init__(s, manager, name, addr, description, ioName):
        s.manager = manager
        s.conf = manager.conf
        s.log = Syslog('Termosensor_%s' % name)
        s._lock = threading.Lock()
        s._name = name
        s._addr = addr
        s._description = description
        s._ioName = ioName
        s.updateTime = 0


    def update(s, t):
        with s._lock:
            s._t = t
            s.updateTime = int(time.time())


    def t(s):
        now = int(time.time())
        with s._lock:
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


    def __repr__(s):
        return "Termosensor:%s" % s.name()