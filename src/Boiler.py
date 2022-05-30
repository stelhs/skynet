import requests
from Exceptions import *
from SubsystemBase import *


class Boiler(SubsystemBase):
    def __init__(s, conf, httpServer):
        super().__init__("boiler", conf)
        s.httpHandlers = Boiler.HttpHandlers(s, httpServer)


    def listenedEvents(s):
        return ['boiler']


    def eventHandler(s, source, type, data): # TODO
        pass


    def send(s, op, args = {}):
        url = "http://%s:%s/%s" % (s.conf['host'], s.conf['port'], url)
        try:
            r = requests.get(url = url, params = args)
            resp = r.json()
            if resp['status'] != 'ok' and resp['reason']:
                raise BoilerError(s.log,
                        "Request '%s' to boiler '%s' return response with error: %s" % (
                                op, s.name(), resp['reason']))
            return resp
        except requests.RequestException as e:
            raise BoilerError(s.log,
                    "Request '%s' to bolier '%s' fails: %s" % (
                            op, s.name, e)) from e
        except json.JSONDecodeError as e:
            raise BoilerError(s.log,
                    "Response for '%s' from boiler '%s' parse error: %s" % (
                            op, s.name, e)) from e
        except KeyError as e:
            raise BoilerError(s.log,
                    "Request '%s' to boiler '%s' return incorrect json: %s" % (
                            op, s.name(), r))


    def setTarget_t(s, t):
        s.send('boiler/set_target_t', {'t': t})


    def boilerEnable(s, args, body, attrs, conn):
        s.send('boiler/enable')


    def heaterEnable(s, args, body, attrs, conn):
        s.send('boiler/fun_heater_enable')


    def heaterDisable(s, args, body, attrs, conn):
        s.send('boiler/fun_heater_disable')



    class HttpHandlers():
        def __init__(s, boiler, httpServer):
            s.boiler = boiler
            s.httpServer = httpServer
            s.httpServer.setReqHandler("GET", "/boiler/set_target_t", s.setTarget_t, ['t'])
            s.httpServer.setReqHandler("GET", "/boiler/boiler_enable", s.boilerEnable)
            s.httpServer.setReqHandler("GET", "/boiler/heater_enable", s.heaterEnable)
            s.httpServer.setReqHandler("GET", "/boiler/heater_disable", s.heaterDisable)


        def setTarget_t(s, args, body, attrs, conn):
            try:
                s.boiler.setTarget_t(args['t'])
            except BoilerError as e:
                raise HttpHandlerError('Can`t set target temperature: %s' % e)



        def boilerEnable(s, args, body, attrs, conn):
            try:
                s.send('boiler/enable')
            except BoilerError as e:
                raise HttpHandlerError('Can`t enable boiler: %s' % e)


        def heaterEnable(s, args, body, attrs, conn):
            try:
                s.send('boiler/fun_heater_enable')
            except BoilerError as e:
                raise HttpHandlerError('Can`t enable heater: %s' % e)


        def heaterDisable(s, args, body, attrs, conn):
            try:
                s.send('boiler/fun_heater_disable')
            except BoilerError as e:
                raise HttpHandlerError('Can`t disable heater: %s' % e)


