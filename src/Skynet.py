from Syslog import *
from ConfSkynet import *
from DatabaseConnector import *
from HttpServer import *
from TelegramClientSkynet import *
from Termosensors import *
from Boiler import *
from WaterSupply import *
from DoorLocks import *
from PowerSockets import *
from Lighters import *
from Gates import *
from Speakerphone import *
from Guard import *
from Io import *
from Ui import *
from Cron import *
from Ups import *




class Skynet():
    def __init__(s):
        s.eventSubscribers = []
        s.log = Syslog("Skynet")
        s.conf = ConfSkynet()
        s.periodicNotifier = PeriodicNotifier()
        s.tc = TelegramClientSkynet(s, s.telegramHandler)
        s.db = DatabaseConnector(s, s.conf.db)
        Task.setErrorCb(s.taskExceptionHandler)

        s.httpServer = HttpServer(s.conf.skynet['http_host'],
                                  s.conf.skynet['http_port'],
                                  s.conf.skynet['http_www'])

        s.cron = Cron()
        s.ts = Termosensors(s)
        s.io = Io(s)
        s.ui = Ui(s)
        s.boiler = Boiler(s)
        s.waterSupply = WaterSupply(s)
        s.doorLocks = DoorLocks(s)
        s.powerSockets = PowerSockets(s)
        s.lighters = Lighters(s)
        s.speakerphone = Speakerphone(s)
        s.gates = Gates(s)
        s.guard = Guard(s)
        s.ups = Ups(s)

        s.httpHandlers = Skynet.HttpHandlers(s, s.httpServer)


    def registerEventSubscriber(s, name, cb, sources=(), evTypes=()):
        subscriber = Skynet.EventSubscriber(name, cb, sources, evTypes)
        s.eventSubscribers.append(subscriber)


    def emitEvent(s, source, evType, data):
        for sb in s.eventSubscribers:
            if not sb.match(source, evType):
                continue
            try:
                sb.cb(source, evType, data)
            except AppError as e:
                s.tc.toAdmin("Error in event handler '%s' for source: '%s', " \
                             "evType: '%s': %s" % (sb.name, source, evType, e))


    def telegramHandler(tc, text, msgId, date, fromName,
                        fromId, chatId, chatType):
        print("received %s" % text)


    def taskExceptionHandler(s, task, errMsg):
        s.tc.sendToChat('stelhs',
                "Skynet: task '%s' error:\n%s" % (task.name(), errMsg))


    def destroy(s):
        s.guard.destroy()
        s.lighters.destroy()
        s.waterSupply.destroy()
        s.ups.destroy()
        s.io.destroy()
        s.httpServer.destroy()
        s.powerSockets.destroy()
        s.doorLocks.destroy()
        s.db.destroy()


    class EventSubscriber():
        def __init__(s, name, cb, sources, evTypes):
            s.cb = cb
            s.sources = sources
            s.evTypes = evTypes
            s.name = name


        def match(s, source, evType):
            sourceMatched = True
            if len(s.sources):
                sourceMatched = False
                if source in s.sources:
                    sourceMatched = True

            evTypeMatched = True
            if len(s.evTypes):
                evTypeMatched = False
                if evType in s.evTypes:
                    evTypeMatched = True

            return sourceMatched and evTypeMatched


        def __repr__(s):
            return "EventSubscriber:%s" % s.name



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



