import threading, time, json
from Exceptions import *
from Task import *
from SkynetStorage import *
from HttpServer import *

class Guard():
    def __init__(s, skynet):
        s.log = Syslog('Guard')
        s.skynet = skynet
        s.conf = skynet.conf.guard
        s.httpServer = skynet.httpServer
        s.db = skynet.db
        s.io = skynet.io
        s.ui = skynet.ui
        s.waterSupply = skynet.waterSupply
        s.gates = skynet.gates
        s.doorLocks = skynet.doorLocks
        s.powerSockets = skynet.powerSockets
        s.speakerphone = skynet.speakerphone
        s.gates = skynet.gates
        s.doorLocks = skynet.doorLocks
        s.boiler = skynet.boiler
        s.tc = skynet.tc

        s.dbw = Guard.Db(s, s.db)
        s.storage = SkynetStorage(skynet, 'guard.json')
        s._lock = threading.Lock()
        s._zones = []
        s.createZones()
        s.startSettings = Guard.StartSettings(s)
        s.stopSettings = Guard.StopSettings(s)
        s.httpHandlers = Guard.HttpHandlers(s)
        s.TgHandlers = Guard.TgHandlers(s)
        s._state = s.storage.key('/state', 'sleep')
        s._stateTime = s.storage.key('/state_time', int(time.time()))
        s._stateId = s.storage.key('/stateId', 0)
        s.watchingZones = s.storage.key('/watchingZones', [])

        s.voicePowerPort = s.io.port("voice_power")
        s.uiUpdater = s.skynet.periodicNotifier.register("guard", s.uiUpdateHandler, 2000)
        s.voicePowerPort.subscribe("Guard", lambda state: s.uiUpdater.call())


    def toSkynet(s, msg):
        s.tc.toSkynet("Guard: %s" % msg)


    def toAdmin(s, msg):
        s.tc.toAdmin("Guard: %s" % msg)


    def createZones(s):
        if len(s._zones):
            raise GuardZonesAlreadyCreatedError(s.log,
                    "createZones() failed: Zones list alrady was created early")
        zones = []
        for name, zConf in s.conf['zones'].items():
            zone = Guard.Zone(s, name, zConf, s.storage, s.db)
            zones.append(zone)
        s._zones = tuple(zones)


    def doSpeakerphoneShutUp(s):
        try:
            s.speakerphone.shutUp()
        except AppError as e:
            s.errors.append(("Can't shutdown speakerphone", e))


    def doSetReadyState(s):
        workshopZones = ['workshop_west', 'workshop_south', 'workshop_north', 'workshop_east']
        watchedZones = [zone.name() for zone in s.zones(unlockedOnly=True) if zone.isReadyToWatch()]

        if s.startSettings.noWatchWorkshop.val:
            watchedZones = list(set(watchedZones) - set(workshopZones))

        s.watchingZones.set(watchedZones)

        s._state.set('ready')
        s._stateTime.set(int(time.time()))
        try:
            stateId = s.db.insert('guard_states',
                                  {'state': 'ready',
                                   'config': s.storage.jsonData()});
            s._stateId.set(stateId)
        except DatabaseConnectorError as e:
            s.errors.append(("Can't insert into table guard_states", e))


    def doLampBlinkOnStart(s):
        try:
            s.io.port('guard_lamp').blink(4000, 1000, 2)
        except AppError as e:
            s.errors.append(("Can't blink guard lamp", e))


    def doLampBlinkAbort(s):
        try:
            s.io.port('guard_lamp').down()
        except AppError as e:
            s.errors.append(("Can't abort blink guard lamp", e))


    def doGatesClose(s):
        try:
            s.gates.close()
        except AppError as e:
            s.errors.append(("Can't close Gates", e))


    def doDoorLocksOnStart(s):
        for dl in s.doorLocks.list():
            st = s.startSettings.doorLocks[dl.name()]
            if st.val:
                try:
                    dl.open()
                except AppError as e:
                    s.errors.append(("Can't open doorLock %s" % dl.name(), e))
            else:
                try:
                    dl.close()
                except AppError as e:
                    s.errors.append(("Can't close doorLock %s" % dl.name(), e))


    def doPowerSocketsOnStart(s):
        for ps in s.powerSockets.list():
            st = s.startSettings.powerSockets[ps.name()]
            if st.val:
                try:
                    ps.up()
                except AppError as e:
                    s.errors.append(("Can't enable power for '%s'" % ps.name(), e))
            else:
                try:
                    ps.down()
                except AppError as e:
                    s.errors.append(("Can't disable power for '%s'" % ps.name(), e))


    def doWaterSupplyOnStart(s):
        if not s.startSettings.waterSupply.val:
            try:
                s.waterSupply.lock()
            except AppError as e:
                s.errors.append(("Can't disable water supply", e))
        else:
            try:
                s.waterSupply.unlock()
            except AppError as e:
                s.errors.append(("Can't enable water supply", e))


    def doBoilerStandby(s):
        try:
            s.boiler.setTarget_t(5.0)
        except AppError as e:
            s.errors.append(("Can't set boiler temperature", e))


    def doSetSleepState(s):
        s._state.set('sleep')
        s._stateTime.set(int(time.time()))
        try:
            stateId = s.db.insert('guard_states',
                                  {'state': 'sleep',
                                   'config': s.storage.jsonData()});
            s._stateId.set(stateId)
        except DatabaseConnectorError as e:
            s.errors.append(("Can't insert into table guard_states", e))


    def doLampBlinkOnStop(s):
        try:
            s.io.port('guard_lamp').blink(500, 500, 6)
        except AppError as e:
            s.errors.append(("Can't blink guard lamp", e))


    def doGatesOpen(s):
        try:
            s.gates.open()
        except AppError as e:
            s.errors.append(("Can't close Gates", e))


    def doPowerSocketsOnStop(s):
        try:
            s.powerSockets.up()
        except AppError as e:
            s.errors.append(("Can't power up", e))


    def doDoorLocksOnStop(s):
        for dl in s.doorLocks.list():
            st = s.stopSettings.doorLocks[dl.name()]
            if st.val:
                try:
                    dl.open()
                except AppError as e:
                    s.errors.append(("Can't open doorLock %s" % dl.name(), e))
            else:
                try:
                    dl.close()
                except AppError as e:
                    s.errors.append(("Can't close doorLock %s" % dl.name(), e))


    def doWaterSupplyOnStop(s):
        if not s.startSettings.waterSupply.val:
            try:
                s.waterSupply.unlock()
            except AppError as e:
                s.errors.append(("Can't enable water supply", e))


    def doBoilerReady(s):
        try:
            s.boiler.setTarget_t(17.0)
        except AppError as e:
            s.errors.append(("Can't set boiler temperature", e))


    def start(s):
        with s._lock:
            s.errors = []

            s.doLampBlinkAbort()
            s.doSpeakerphoneShutUp()
            s.doSetReadyState()

            if s.isStarted():
                s.uiInfo('Updated guard settings')
                s.doDoorLocksOnStart()
                s.doPowerSocketsOnStart()
                s.doWaterSupplyOnStart()
            else:
                s.doLampBlinkOnStart()
                s.doGatesClose()
                s.doDoorLocksOnStart()
                s.doPowerSocketsOnStart()
                s.doWaterSupplyOnStart()
                s.doBoilerStandby()

            try:
                s.toSkynet("Охрана включена");

                notWatchedZoneNames = [zone.description() for zone in s.zones() if zone.name() not in s.watchingZones.val]
                notWatchedZonesText = "\n\t".join(notWatchedZoneNames)
                s.toSkynet("Зоны не под охраной:\n\t%s" % notWatchedZonesText);
            except AppError as e:
                pass

            if len(s.errors):
                shortListText = "<br> ".join([row[0] for row in s.errors])
                try:
                    fullListText = ";\n ".join(["%s: %s\n\n" % row for row in s.errors])
                    s.toSkynet("Охрана включена, но возникли ошибки: \n%s" % fullListText);
                except AppError:
                    pass
                raise GuardError(s.log, "Guard was started but any errors has occured: %s" % shortListText)

    #        s.uiInfo('Guard ')


    #        $this->send_screnshots();
     #       $this->send_video_url($event_time);


    def stop(s):
        with s._lock:
            s.errors = []
            s.doLampBlinkAbort()
            s.doSpeakerphoneShutUp()
            s.doSetSleepState()
            s.doGatesOpen()
            s.doLampBlinkOnStop()
            s.doPowerSocketsOnStop()
            s.doDoorLocksOnStop()
            s.doWaterSupplyOnStop()
            s.doBoilerReady()

            if len(s.errors):
                shortListText = "<br> ".join([row[0] for row in s.errors])
                try:
                    fullListText = ";\n ".join(["%s: %s\n\n" % row for row in s.errors])
                    s.toSkynet("Охрана отключена, но возникли ошибки: \n%s" % fullListText);
                except AppError:
                    pass
                raise GuardError(s.log, "Guard was stopped but any errors has occured: %s" % shortListText)

            try:
                s.toSkynet("Охрана отключена");
            except AppError as e:
                pass


    def isStarted(s):
        return s._state.val == 'ready'


    def isReadyToWatchSensors(s):
        if not s.isStarted():
            return False

        now = int(time.time())
        if (now - s._stateTime.val) > s.conf['start_interval']:
            return True
        return False


    def zoneTrig(s, zone):
        try:
            alarmId = s.db.insert('guard_alarms',
                                  {'zone': zone.name(),
                                   'state_id': s._stateId.val});
        except DatabaseConnectorError as e:
            s.errors.append(("Can't insert into table guard_alarms", e))

        s.tc.toAlarm("!!! Внимание, Тревога !!!\n" \
                     "Сработала зона: '%s', событие: %d" % (
                     zone.name(), s._stateId.val))


    def zones(s, unlockedOnly=False):
        if unlockedOnly:
            return [zone for zone in s._zones if not zone.isBlocked()]
        return s._zones


    def zone(s, zName):
        for zone in s.zones():
            if zone.name() == zName:
                return zone
        raise GuardZoneNotRegistredError(s.log, "Zone %s has not registred" % zName)


    def sensor(s, sName):
        for zone in s.zones():
            for sensor in zone.sensors():
                if sensor.name() == sName:
                    return sensor

        raise GuardSensorNotRegistredError(s.log, "Sensor %s has not registred" % sName)


    def uiErr(s, msg):
        s.skynet.emitEvent('guard', 'error', msg)


    def uiInfo(s, msg):
        s.skynet.emitEvent('guard', 'info', msg)


    def uiUpdateHandler(s):
        leds = {}
        notAllReady = False
        blockedZonesExisted = False

        for zone in s.zones():
            leds['ledGuardZoneReady_%s' % zone.name()] = zone.isReadyToWatch()
            blocked = zone.isBlocked()
            if blocked:
                blockedZonesExisted = True
            leds['ledGuardZoneBlocked_%s' % zone.name()] = blocked

            for sensor in zone.sensors():
                isTriggered = sensor.isTriggered()
                try:
                    leds['ledGuardSensorState_%s' % zone.name()] = sensor.state()
                except IoError:
                    continue

                if isTriggered:
                    notAllReady = True

        leds['ledGuardNotWatchedZones'] = notAllReady
        leds['ledGuardAllZonesReady'] = not notAllReady
        leds['ledGuardBlockedZones'] = blockedZonesExisted

        try:
            leds['ledGuardPublicAudio'] = s.voicePowerPort.state()
        except IoError:
            pass

        s.skynet.emitEvent('guard', 'ledsUpdate', leds)


    def destroy(s):
        with s._lock:
            print("destroy Guard")
            s.storage.destroy()


    class HttpHandlers():
        def __init__(s, guard):
            s.guard = guard
            s.skynet = guard.skynet
            s.regUiHandler('w', "GET", "/guard/zone_lock_unlock", s.zoneLockUnlockHandler, ('zone_name', ))
            s.regUiHandler('r', "GET", "/guard/obtain_settings", s.obtainSettingsHandler)
            s.regUiHandler('w', "POST", "/guard/start_with_settings", s.startWithSettingsHandler)
            s.regUiHandler('w', "POST", "/guard/stop_with_settings", s.stopWithSettingsHandler)
            s.regUiHandler('w', "GET", "/guard/stop_public_sound", s.stopPublicSoundHandler)


        def regUiHandler(s, permissionMode, method, url, handler,
                                requiredFields=[], retJson=True):
            s.skynet.ui.setReqHandler('guard', permissionMode, method,
                                      url, handler, requiredFields, retJson)


        def zoneLockUnlockHandler(s, args, conn):
            try:
                zone = s.guard.zone(args['zone_name'])
                if zone.isBlocked():
                    zone.unlock()
                else:
                    zone.lock()
                s.guard.uiUpdater.call()
            except GuardZoneNotRegistredError as e:
                raise HttpHandlerError('Can`t switch zone lock/unlock: %s' % e)


        def obtainSettingsHandler(s, args, conn):
            data = {'startSettings': s.guard.startSettings.asDict(),
                    'stopSettings': s.guard.stopSettings.asDict()}
            s.guard.skynet.emitEvent('guard', 'guardSettings', data)


        def startWithSettingsHandler(s, args, conn):
            body = conn.body()
            try:
                data = json.loads(body)
                s.guard.startSettings.fromDict(data)
            except json.JSONDecodeError as e:
                raise HttpHandlerError("Can't set start settings. Json data is not valid: %s" % e)
            except KeyError as e:
                raise HttpHandlerError("Settings data format error. Field %s is absent" % e)

            try:
                s.guard.start()
            except AppError as e:
                raise HttpHandlerError("Can't starting guard: %s" % e)

            try:
                s.guard.uiUpdater.call()
            except AppError as e:
                raise HttpHandlerError("Guard was started but UI notifier error: %s" % e)


        def stopWithSettingsHandler(s, args, conn):
            body = conn.body()
            try:
                data = json.loads(body)
                s.guard.stopSettings.fromDict(data)
            except json.JSONDecodeError as e:
                raise HttpHandlerError("Can't set stop settings. Json data is not valid: %s" % e)
            except KeyError as e:
                raise HttpHandlerError("Settings data format error. Field %s is absent" % e)

            try:
                s.guard.stop()
            except AppError as e:
                raise HttpHandlerError("Can't stopped guard: %s" % e)

            try:
                s.guard.uiUpdater.call()
            except AppError as e:
                raise HttpHandlerError("Guard was stopped but UI notifier error: %s" % e)


        def stopPublicSoundHandler(s, args, conn):
            try:
                s.guard.speakerphone.shutUp()
            except AppError as e:
                raise HttpHandlerError("Can't stop public sound: %s" % e)


    class TgHandlers():
        def __init__(s, guard):
            s.guard = guard
            s.tc = guard.tc

            s.tc.registerHandler('guard', s.stop, 'w', ('отключи охрану', 'guard stop'))
            s.tc.registerHandler('guard', s.start, 'w', ('включи охрану', 'guard start'))


        def stop(s, arg, replyFn):
            replyFn("Делаю...")
            try:
                s.guard.stop()
            except AppError as e:
                replyFn("Возникли ошибки: %s" % e)


        def start(s, arg, replyFn):
            replyFn("Делаю...")
            try:
                s.guard.start()
            except AppError as e:
                replyFn("Возникли ошибки: %s" % e)


    class StartSettings():
        def __init__(s, guard):
            s.guard = guard
            s.st = guard.storage

            s.noWatchWorkshop = s.st.key('/startSettings/noWatchWorkshop', False)

            s.powerSockets = {}
            for ps in s.guard.powerSockets.list():
                s.powerSockets[ps.name()] = s.st.key('/startSettings/power/%s' % ps.name(), False)

            s.doorLocks = {}
            for dl in s.guard.doorLocks.list():
                s.doorLocks[dl.name()] = s.st.key('/startSettings/doorLocks/%s' % dl.name(), False)

            s.waterSupply = s.st.key('/startSettings/waterSupply', False)

            s.enabledAlarmSound = s.st.key('/startSettings/enabledAlarmSound', False)
            s.enabledSMS = s.st.key('/startSettings/enabledSMS', False)
            s.enabledSkynetGroupNotify = s.st.key('/startSettings/enabledSkynetGroupNotify', False)


        def asDict(s):
            data = {}
            data['swGuardStartingNoWatchWorkshop'] = s.noWatchWorkshop.val
            data['swGuardStartingWaterSupply'] = s.waterSupply.val
            data['swGuardAlarmSoundEnabled'] = s.enabledAlarmSound.val
            data['swGuardAlarmSmsEnabled'] = s.enabledSMS.val
            data['swGuardAlarmSkynetEnabled'] = s.enabledSkynetGroupNotify.val

            for name, key in s.powerSockets.items():
                data['swGuardStartingPowerZone_%s' % name] = s.powerSockets[name].val

            for name, key in s.doorLocks.items():
                data['swGuardStartingDoorlockPower_%s' % name] = s.doorLocks[name].val
            return data


        def fromDict(s, data):
            if 'swGuardStartingNoWatchWorkshop' in data:
                s.noWatchWorkshop.set(data['swGuardStartingNoWatchWorkshop'])

            if 'swGuardStartingWaterSupply' in data:
                s.waterSupply.set(data['swGuardStartingWaterSupply'])

            if 'swGuardAlarmSoundEnabled' in data:
                s.enabledAlarmSound.set(data['swGuardAlarmSoundEnabled'])

            if 'swGuardAlarmSmsEnabled' in data:
                s.enabledSMS.set(data['swGuardAlarmSmsEnabled'])

            if 'swGuardAlarmSkynetEnabled' in data:
                s.enabledSkynetGroupNotify.set(data['swGuardAlarmSkynetEnabled'])

            for name, key in s.powerSockets.items():
                divName = 'swGuardStartingPowerZone_%s' % name
                if divName in data:
                    s.powerSockets[name].set(data[divName])

            for name, key in s.doorLocks.items():
                divName = 'swGuardStartingDoorlockPower_%s' % name
                if divName in data:
                    s.doorLocks[name].set(data[divName])



    class StopSettings():
        def __init__(s, guard):
            s.guard = guard
            s.st = guard.storage

            s.openGates = s.st.key('/stopSettings/openGates', True)
            s.stopDvr = s.st.key('/stopSettings/stopDvr', True)

            s.doorLocks = {}
            for dl in s.guard.doorLocks.list():
                s.doorLocks[dl.name()] = s.st.key('/stopSettings/doorLocks/%s' % dl.name(), True)


        def asDict(s):
            data = {}
            data['openGates'] = s.openGates.val
            data['stopDvr'] = s.stopDvr.val

            for name, key in s.doorLocks.items():
                data['swGuardStoppingDoorlockPower_%s' % name] = s.doorLocks[name].val

            return data


        def fromDict(s, data):
            if 'openGates' in data:
                s.openGates.set(data['openGates'])

            if 'stopDvr' in data:
                s.stopDvr.set(data['stopDvr'])

            for name, key in s.doorLocks.items():
                divName = 'swGuardStoppingDoorlockPower_%s' % name
                if divName in data:
                    s.doorLocks[name].set(data[divName])


    class Db():
        def __init__(s, guard, db):
            s.guard = guard
            s.db = db



    class Zone():
        def __init__(s, guard, name, conf, storage, db):
            s.guard = guard
            s.io = guard.io
            s._lock = threading.Lock()
            s.storage = storage
            s._name = name
            s._desc = conf['desc']
            if len(conf['io_sensors']) > 1:
                s._diffInterval = conf['diff_interval']
            s._alarmInterval = conf['alarm_interval']
            s._features = conf['features']
            s._sensors = []
            s._blocked = s.storage.key('/zones/zone_%s/blocked' % s.name(), False)

            for sName, trigState in conf['io_sensors'].items():
                port = s.guard.io.port(sName)
                if port.mode() != 'in':
                    raise GuardZoneCreateError(s.log,
                            "Can't create zone '%s': port '%s' has incorrect type '%s'. " \
                            "Only 'in' ports allowable" % (sName, port.name(), port.mode()))

                sensor = Guard.Sensor(s.io, s, port, trigState)
                s._sensors.append(sensor)


        def name(s):
            return s._name


        def description(s):
            return s._desc


        def sensors(s):
            return s._sensors


        def isBlocked(s):
            with s._lock:
                return s._blocked.val


        def lock(s):
            if s.isBlocked():
                return

            with s._lock:
                s._blocked.set(True)


        def unlock(s):
            if not s.isBlocked():
                return
            with s._lock:
                s._blocked.set(False)


        def isReadyToWatch(s):
            for sense in s._sensors:
                if sense.isTriggered():
                    return False
            return True


        def sensorTrig(s, triggeredSensor):
            if len(s._sensors) == 1:
                return s.guard.zoneTrig(s)

            minInterval = None
            for sensor in s._sensors:
                if sensor == triggeredSensor:
                    continue

                interval = triggeredSensor.trigTime() - sensor.trigTime()
                if not minInterval:
                    minInterval = interval

                if interval < minInterval:
                    minInterval = interval

            if minInterval > s._diffInterval:
                return

            print("call zone %s trig" % s.name())
            s.guard.zoneTrig(s)


        def __repr__(s):
            return "zone:%s" % s.name()


    class Sensor():
        def __init__(s, io, zone, port, trigState):
            s._lock = threading.Lock()
            s.io = io
            s.zone = zone
            s.guard = zone.guard
            s.tc = s.guard.tc
            s.port = port
            s.attemptToLockTimer = None
            s.storage = s.guard.storage

            s.trigState = trigState
            port.subscribe("Sensor", s.doEventProcessing)

            s._blocked = s.storage.key('/zones/zone_%s/sensor_%s/blocked' % (
                                       s.zone.name(), s.name()), False)
            s._lastTrigTime = s.storage.key('/zones/zone_%s/sensor_%s/last_trig_time' % (
                                            s.zone.name(), s.name()),
                                            int(time.time()))
            s._lastNotificationTime = s.storage.key('/zones/zone_%s/sensor_%s/last_notification_time' % (
                                                    s.zone.name(), s.name()),
                                                    int(time.time()))
            s._trigCnt = s.storage.key('/zones/zone_%s/sensor_%s/trig_cnt' % (
                                       s.zone.name(), s.name()), 0)


        def trigTime(s):
            return s._lastTrigTime.val


        def isTriggered(s):
            try:
                return s.state() == s.trigState
            except IoError:
                return False


        def isBlocked(s):
            with s._lock:
                return s._blocked.val


        def attemptToAutoUnlock(s):
            if not s.isBlocked():
                return

            now = int(time.time())
            if (now - s._lastTrigTime.val) > s.guard.conf["sensorAutolock"]["unlockInterval"]:
                s.unlock()
                s.toAdmin("Датчик %s из зоны %s автоматически разблокирован" % (
                             s.name(), s.zone.name()))

            return s._blocked.val


        def lock(s):
            if s.isBlocked():
                return

            with s._lock:
                s._blocked.set(True)
            s._lastNotificationTime.set(int(time.time()))
            s._trigCnt.set(0)
            print("sensor %s locked" % s.name())


        def unlock(s):
            if not s.isBlocked():
                return
            with s._lock:
                s._blocked.set(False)
            s._trigCnt.set(0)
            print("sensor %s ulocked" % s.name())


        def match(s, port):
            return port.name() == s.port.name()


        def state(s):
            return s.port.state()


        def name(s):
            return s.port.name()


        def doEventProcessing(s, state):
            s.zone.guard.uiUpdater.call()

            if s.zone.isBlocked():
                return

            if s.trigState != state:
                return

            now = int(time.time())
            if (now - s._lastTrigTime.val) < 3:
                return

            if not s.guard.isReadyToWatchSensors():
                return

            print("doEventProcessing %s" % s.name())

            s.attemptToAutoUnlock()
            s._lastTrigTime.set(now)
            s._trigCnt.set(s._trigCnt.val + 1)

            if s.isBlocked():
                print("blocked")
                if (now - s._lastNotificationTime.val) > s.guard.conf['sensorAutolock']['notoficationInterval']:
                    s.toAdmin("Заблокированный датчик продолжает генерировать события. " \
                                 "Нагенерировано событий: %d" % s._trigCnt.val)
                    s._lastNotificationTime.set(now)
                return

            if not s.attemptToLockTimer:
                print("start attemptToLockTimer %s" % s.name())
                s.attemptToLockTimer = now

            if (now - s.attemptToLockTimer) >= s.guard.conf['sensorAutolock']['interval']:
                print("sensorAutolock > 5min: %s" % s.name())
                if s._trigCnt.val < s.guard.conf['sensorAutolock']['trigNumber']:
                    print("cnt < 5: %s" % s.name())
                    s._trigCnt.set(0)
                    s.attemptToLockTimer = None
                else:
                    print("cnt > 5: %s" % s.name())
                    s.lock()
                    s.attemptToLockTimer = None
                    s.toAdmin("Датчик %s из зоны %s заблокирован, " \
                                 "потому что он сработал более 5ти раз за 5 минут" % (
                                 s.name(), s.zone.name()))
                    return

            print("call zone trig by %s" % s.name())
            s.zone.sensorTrig(s)


        def __repr__(s):
            return "sensor:%s" % s.name()




