import datetime
from Exceptions import *
from Syslog import *
from HttpServer import *
from Storage import *


class Lighters():
    def __init__(s, skynet):
        s.skynet = skynet
        s.tc = skynet.tc
        s.log = Syslog('Lighters')
        s.conf = skynet.conf.lighters
        s.io = skynet.io
        s.httpServer = skynet.httpServer
        s._lighters = []
        s.httpHandlers = Lighters.HttpHandlers(s)
        s.TgHandlers = Lighters.TgHandlers(s)

        s.storage = Storage('lighters.json')
        s._enableAutomatic = s.storage.key('/automatic', True)

        for name, inf in s.conf['lighters'].items():
            l = Lighters.Lighter(s, name, inf['description'], inf['port'])
            s._lighters.append(l)


        s.skynet.cron.registerEveryMin('lighter_automatic', s.timeHandler)
        s.uiUpdater = s.skynet.periodicNotifier.register("lighters", s.uiUpdateHandler, 2000)
        s.initAutomtic()


    def initAutomtic(s):
        if not s._enableAutomatic.val:
            return

        if s.isNight():
            s.up()
            s.timesOfDay = 'night'
        else:
            s.timesOfDay = 'day'
            s.down()


    def timeHandler(s):
        if not s._enableAutomatic.val:
            return

        if s.isNight() and s.timesOfDay == 'day':
            try:
                s.up()
            except AppError as e:
                s.tc.toAdmin('Неполучилось включить освещение: %s' % e)
            s.timesOfDay = 'night'

        if not s.isNight() and s.timesOfDay == 'night':
            try:
                s.down()
            except AppError as e:
                s.tc.toAdmin('Неполучилось отключить освещение: %s' % e)
                s.timesOfDay = 'day'


    def isNight(s):
        now = datetime.datetime.now()
        start, end = s.conf['light_calendar'][str(now.month)]

        parts = start.split(':')
        startHour = int(parts[0])
        startMin = int(parts[1])

        parts = end.split(':')
        endHour = int(parts[0])
        endMin = int(parts[1])

        if now.hour == startHour and now.minute > startMin:
            return True

        if now.hour > startHour:
            return True

        if now.hour == endHour and now.minute <= endMin:
            return True

        if now.hour < endHour:
            return True

        return False


    def list(s):
        return s._lighters


    def up(s):
        for lighter in s.list():
            lighter.up()


    def down(s):
        for lighter in s.list():
            lighter.down()


    def lighter(s, name):
        for l in s.list():
            if l.name() == name:
                return l
        raise LighterError(s.log, "Lighter '%s' is not registred" % name)


    def uiUpdateHandler(s):
        data = {}
        for l in s.list():
            try:
                data[l.name()] = not l.isDown()
            except AppError:
                pass

        data['automatic'] = s._enableAutomatic.val
        s.skynet.emitEvent('lighters', 'statusUpdate', data)


    def destroy(s):
        print("destroy Lighters")
        s.storage.destroy()




    class HttpHandlers():
        def __init__(s, manager):
            s.manager = manager
            s.skynet = manager.skynet
            s.regUiHandler('w', "GET", "/lighters/on", s.lighterOnHandler, ('name', ))
            s.regUiHandler('w', "GET", "/lighters/off", s.lighterOffHandler, ('name', ))
            s.regUiHandler('w', "GET", "/lighters/switch_automatic_control", s.autoControlSwitchHandler)


        def regUiHandler(s, permissionMode, method, url, handler,
                                requiredFields=[], retJson=True):
            s.skynet.ui.setReqHandler('lighters', permissionMode, method,
                                      url, handler, requiredFields, retJson)


        def lighterOnHandler(s, args, conn):
            try:
                name = args['name']
                lighter = s.manager.lighter(name)
                lighter.up()
            except AppError as e:
                raise HttpHandlerError("Can't turn on lighter %s: %s" % (name, e))


        def lighterOffHandler(s, args, conn):
            try:
                name = args['name']
                lighter = s.manager.lighter(name)
                lighter.down()
            except AppError as e:
                raise HttpHandlerError("Can't turn off lighter %s: %s" % (name, e))


        def autoControlSwitchHandler(s, args, conn):
            if s.manager._enableAutomatic.val:
                s.manager._enableAutomatic.set(False)
            else:
                s.manager._enableAutomatic.set(True)
            s.manager.uiUpdater.call()


    class TgHandlers():
        def __init__(s, manager):
            s.manager = manager
            s.tc = manager.tc

            s.tc.registerHandler('lighters', s.on, 'w', ('включи свет', 'lighters on'))
            s.tc.registerHandler('lighters', s.off, 'w', ('отключи свет', 'lighters off'))


        def on(s, arg, replyFn):
            try:
                s.manager.up()
            except AppError as e:
                return replyFn("Не удалось включить свет: %s" % e)
            replyFn("Свет включён")


        def off(s, arg, replyFn):
            try:
                s.manager.down()
            except AppError as e:
                return replyFn("Не удалось отключить свет: %s" % e)
            replyFn("Свет выключён")



    class Lighter():
        def __init__(s, manager, name, description, pName):
            s.manager = manager
            s._name = name
            s._description = description
            s._port = s.manager.io.port(pName)
            s._port.subscribe("Lighter", lambda state: s.manager.uiUpdater.call())


        def name(s):
            return s._name


        def up(s):
            s._port.up()


        def down(s):
            s._port.down()


        def isDown(s):
            return not s._port.cachedState()


        def __repr__(s):
            return "Lighter:%s" % s.name()



