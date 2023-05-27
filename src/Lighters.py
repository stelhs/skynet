import datetime, time
from Exceptions import *
from Syslog import *
from HttpServer import *
from SkynetStorage import *
from TimeRange import *


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
        s.timesOfDay = None

        s.storage = SkynetStorage(skynet, 'lighters.json')
        s._enableAutomatic = s.storage.key('/automatic', True)

        for name, inf in s.conf['lighters'].items():
            l = Lighters.Lighter(s, name, inf['description'], inf['port'])
            s._lighters.append(l)


        s.skynet.cron.register('lighterAutomatic', ('0 */1 * * * *',)).addCb(s.cronHandler)
        s.uiUpdater = s.skynet.periodicNotifier.register("lighters", s.uiUpdateHandler, 2000)


    def cronHandler(s, cronWorker=None):
        if not s._enableAutomatic.val:
            return

        if not s.timesOfDay:
            if s.isNight():
                try:
                    s.up()
                except AppError as e:
                    s.tc.toAdmin('Неполучилось включить освещение: %s' % e)
                s.timesOfDay = 'night'
                return

            try:
                s.down()
            except AppError as e:
                s.tc.toAdmin('Неполучилось отключить освещение: %s' % e)
            s.timesOfDay = 'day'
            return

        if s.isNight() and s.timesOfDay == 'day':
            try:
                s.up()
            except AppError as e:
                s.tc.toAdmin('Неполучилось включить освещение: %s' % e)
                return
            s.timesOfDay = 'night'

        if not s.isNight() and s.timesOfDay == 'night':
            try:
                s.down()
            except AppError as e:
                s.tc.toAdmin('Неполучилось отключить освещение: %s' % e)
                return
            s.timesOfDay = 'day'


    def isNight(s):
        now = datetime.datetime.now()
        rangeStr = s.conf['light_calendar'][str(now.month)]
        tr = TimeRange(rangeStr)
        return tr.isInEntry(now)


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
                data['ledLighter_%s' % l.name()] = not l.isDown()
            except IoError:
                pass

        data['ledLighter_automatic'] = s._enableAutomatic.val
        s.skynet.emitEvent('lighters', 'ledsUpdate', data)


    def textStat(s):
        text = "Уличное освещение:\n"
        for l in s.list():
            try:
                text += "    Фонарь '%s': %s\n" % (l.description(),
                            'выключен' if l.isDown() else ('включен в течении %s' % timeDurationStr(l.upTime())))
            except AppError as e:
                text += "    Не удалось запросить сосотояние фонаря '%s': %s" % (l.description(), e)
        return text


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
            s._startTime = None
            s._port = s.manager.io.port(pName)
            s._port.subscribe("Lighter", lambda state: s.manager.uiUpdater.call())


        def name(s):
            return s._name


        def description(s):
            return s._description


        def up(s):
            s._port.up()
            s._startTime = now()


        def upTime(s):
            if s.isDown():
                return None
            if not s._startTime:
                return 0
            return now() - s._startTime


        def down(s):
            s._port.down()
            s.startTime = None


        def isDown(s):
            return not s._port.state()


        def __repr__(s):
            return "Lighter:%s" % s.name()



