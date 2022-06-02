def skynet():
    if not hasattr(skynet, 'instance'):
        skynet.instance = Skynet()
    return skynet.instance

from Syslog import *
from ConfSkynet import *
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
        s.conf = ConfSkynet()
        s.db = DatabaseConnector(s.conf.db)
        s.tc = TelegramClient(s.conf.telegram, s.telegramHandler)
        Task.setErrorCb(s.taskExceptionHandler)

        s.httpServer = HttpServer(s.conf.skynet['http_host'],
                                  s.conf.skynet['http_port'],
                                  s.conf.skynet['http_www'])

        s.ts = Termosensors(s.conf.termosensors, s.httpServer)
        s.io = Io(s.conf.io, s.httpServer, s.db)
        s.boiler = Boiler(s.conf.boiler, s.httpServer, s.db)
        s.ui = Ui(s.httpServer, s.io)

        s.subsystems = [s.ts, s.io, s.boiler, s.ui]

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
                subsystem.eventHandler(source, evType, data)


    def telegramHandler(tc, text, msgId, date, fromName,
                        fromId, chatId, chatType):
        print("received %s" % text)


    def taskExceptionHandler(s, task, errMsg):
        s.tc.sendToChat('stelhs',
                "Skynet: task '%s' error:\n%s" % (task.name(), errMsg))


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



