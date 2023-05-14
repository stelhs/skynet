from Syslog import *
from ConfSkynet import *
from DatabaseConnector import *
from HttpServer import *
from TelegramClientSkynet import *
from Users import *
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
from Termosensors import *
from Ups import *
from GsmModem import *
from Dvr import *



class Skynet():
    def __init__(s):
        s.eventSubscribers = []
        s.log = Syslog("Skynet")
        s.conf = ConfSkynet()
        s.periodicNotifier = PeriodicNotifier()

        s.tc = None
        s.db = DatabaseConnector(s, s.conf.db)
        s.tc = TelegramClientSkynet(s)
        Task.setErrorCb(s.taskExceptionHandler)

        s.httpServer = HttpServer(s.conf.skynet['http_host'],
                                  s.conf.skynet['http_port'],
                                  s.conf.skynet['http_www'])

        s.users = Users(s)
        s.cron = Cron()
        s.ts = Termosensors(s)
        s.ui = Ui(s)
        s.io = Io(s)
        s.ui.init()
        s.boiler = Boiler(s)
        s.waterSupply = WaterSupply(s)
        s.doorLocks = DoorLocks(s)
        s.powerSockets = PowerSockets(s)
        s.lighters = Lighters(s)
        s.speakerphone = Speakerphone(s)
        s.gates = Gates(s)
        s.guard = Guard(s)
        s.ups = Ups(s)
        s.gsmModem = GsmModem(s)
        s.dvr = Dvr(s)

        s.httpHandlers = Skynet.HttpHandlers(s, s.httpServer)
        s.TgHandlers = Skynet.TgHandlers(s)

        s.tc.toAdmin("Skynet запущен")



    def registerEventSubscriber(s, name, cb, sources=(), evTypes=()):
        subscriber = Skynet.EventSubscriber(name, cb, sources, evTypes)
        s.eventSubscribers.append(subscriber)


    def unsubscribeEvents(s, name):
        for es in s.eventSubscribers:
            if es.name == name:
                s.eventSubscribers.remove(es)
                return


    def emitEvent(s, source, evType, data):
        for sb in s.eventSubscribers:
            if not sb.match(source, evType):
                continue
            try:
                sb.cb(source, evType, data)
            except AppError as e:
                s.tc.toAdmin("Error in event handler '%s' for source: '%s', " \
                             "evType: '%s': %s" % (sb.name, source, evType, e))


    def taskExceptionHandler(s, task, errMsg):
        s.tc.toAdmin("Skynet: task '%s' error:\n%s" % (task.name(), errMsg))


    def catchEvent(s, source=None, evType=None):
        def eventHandler(source, type, data):
            print('catched source = %s, evType = %s, data = %s' % (source, type, data))

        source = (source, ) if source else ()
        evType = (evType, ) if evType else ()
        s.registerEventSubscriber('catchEvent', eventHandler, source, evType)
        try:
            Task.sleep(15000)
        except KeyboardInterrupt:
            pass
        s.unsubscribeEvents('catchEvent')


    def __repr__(s):
        text = "Skynet:\n"
        text += "\ts.cron: Skynet cron\n"
        text += "\ts.ts: Termosensors\n"
        text += "\ts.ui: User Interface\n"
        text += "\ts.io: I/O subsystem\n"
        text += "\ts.boiler: Boiler\n"
        text += "\ts.waterSupply: Water supply system\n"
        text += "\ts.doorLocks: Door locks\n"
        text += "\ts.powerSockets: Power Sockets\n"
        text += "\ts.lighters: Outside lighters\n"
        text += "\ts.speakerphone: Speakerphone\n"
        text += "\ts.gates: Main gates\n"
        text += "\ts.guard: Guard system\n"
        text += "\ts.ups: UPS system\n"
        text += "\ts.gsmModem: USB 3g GSM modem\n"
        text += "\ts.dvr: Digital Video Recorder\n"
        return text


    def destroy(s):
        s.tc.toAdmin("Skynet остановлен")
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


        def eventHandler(s, args, conn):
            try:
                dt = json.loads(conn.body())
                source = dt['source']
                evType = dt['type']
                data = dt['data']
            except json.JSONDecodeError as e:
                raise HttpHandlerError("can't parse JSON from POST request: %s" % e, 'JSONDecodeError')
            except KeyError as e:
                raise HttpHandlerError("%s field not specified in JSON" % e, 'KeyError')

            s.skynet.emitEvent(source, evType, data)


    class TgHandlers():
        def __init__(s, skynet):
            s.skynet = skynet
            s.tc = skynet.tc

            s.tc.registerHandler('skynet', s.status, 'r', ('статус', 'status'))


        def status(s, arg, replyFn):
            replyFn("делаю...")
            subSystems = (s.skynet.guard, s.skynet.gates, s.skynet.doorLocks,
                          s.skynet.powerSockets, s.skynet.ts,
                          s.skynet.boiler, s.skynet.waterSupply,
                          s.skynet.lighters, s.skynet.ups,
                          s.skynet.gsmModem, s.skynet.dvr)
            text = ""
            for sb in subSystems:
                text += "%s\n" % sb.textStat()
            replyFn(text)



