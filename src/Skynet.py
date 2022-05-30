from Syslog import *
from Conf import *
from DatabaseConnector import *
from HttpServer import *
from TelegramClient import *
from Termosensors import *
from Boiler import *
from Io import *
from Ui import *


class Skynet():
    def __init__(s):
        s.log = Syslog("Skynet")
        s.conf = Conf()
        s.db = DatabaseConnector(s.conf.db)
        s.tc = TelegramClient(s.conf.telegram, s.telegramHandler)
        Task.setErrorCb(s.exceptionHandler)

        s.httpServer = HttpServer(s.conf.skynet['http_host'],
                                  s.conf.skynet['http_port'],
                                  s.conf.skynet['http_www'])

        s.subsystems = [Termosensors(s.conf.termosensors, s.httpServer),
                       Io(s.conf.io, s.httpServer, s.db),
                       Boiler(s.conf.boiler, s.httpServer),
                       Ui(s.httpServer)]

        s.httpHandlers = Skynet.HttpHandlers(s, s.httpServer)



    def subsystemByName(s, name):
        for subsystem in s.subsystems:
            if subsystem.name() == name:
                return subsystem
        raise AppError(s.log,
                "subsystemByName() failed: Subsystem '%s' has not registred" % name)


    def emitEvent(s, source, evType, data):
        for subsystem in s.subsystems:
            if source in subsystem.listenedEvents():
                try:
                    subsystem.eventHandler(source, evType, data)
                except:
                    pass


    def telegramHandler(tc, text, msgId, date, fromName,
                        fromId, chatId, chatType):
        print("received %s" % text)


    def exceptionHandler(s, task, errMsg):
        s.tc.sendToChat('stelhs',
                "Skynet Task '%s' error:\n%s" % (task.name(), errMsg))


    def destroy(s):
        s.httpServer.destroy()


    class HttpHandlers():
        def __init__(s, skynet, httpServer):
            s.skynet = skynet
            s.httpServer = httpServer
            s.httpServer.setReqHandler("POST", "/send_event", s.eventHandler)


        def eventHandler(s, args, body, attrs, conn):
            try:
                dt = json.loads(body)
                source = dt['source']
                evType = dt['type']
                data = dt['data']
            except json.JSONDecodeError as e:
                raise HttpHandlerError("can't parse JSON from POST request: %s" % e, 'JSONDecodeError')
            except KeyError as e:
                raise HttpHandlerError("%s field not specified in JSON" % e, 'KeyError')

            s.skynet.emitEvent(source, evType, data)



