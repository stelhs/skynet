import threading
from Exceptions import *
from Syslog import *
from HttpServer import *
from Storage import *


class Ups():
    def __init__(s, skynet):
        s.skynet = skynet
        s.ui = skynet.ui
        s.tc = skynet.tc
        s.db = skynet.db
        s.httpServer = skynet.httpServer
        s.dbw = Ups.Db(s)
        s.log = Syslog('Ups')
        s._lock = threading.Lock()

        s.noVoltage = False
        s.upsTask = Task.setPeriodic('ups', 1000, s.taskUps)

        s.storage = Storage('ups.json')
        s._mode = s.storage.key('/mode', 'charge') # 'charge', 'discharge', 'waiting', 'stopped'
        s._automaticEnabled = s.storage.key('/charger/automatic_enabled', True)


        s._dischargeReason = s.storage.key('/discharge/reason', None) # 'test', 'power_loss'
        s._dischargeStartTime = s.storage.key('/discharge/start_time', 0)
        s._dischargeStopTime = s.storage.key('/discharge/stop_time', 0)
        s._dischargeStartVoltage = s.storage.key('/discharge/start_voltage', None)
        s._dischargeStopVoltage = s.storage.key('/discharge/stop_voltage', None)
        s._dischargeStatusId = s.storage.key('/discharge/status_id', 0)

        s.hw = Ups.Hw(s)
        s.hw.subscribe('ups', s.inputPowerEventHandler, 'inputUpsPower')
        s.hw.subscribe('ups', s.extPowerEventHandler, 'extPower')

        s.charger = Ups.Charger(s)

        s.uiUpdater = s.ui.periodicNotifier.register("ups", s.uiUpdateHandler, 2000)
        s.init()
        s.httpHandlers = Ups.HttpHandlers(s)


    def init(s):
        if s.isDischarge():
            s.enterToPowerLoss()

        if s.mode() == 'discharge' and not s.isDischarge():
            s.chargerStart(1)
            return

        if s.mode() == 'charge':
            s.chargerStart(1)


    def enterToPowerLoss(s):
        now = int(time.time())
        s.setMode('discharge')
        reason = 'power_loss' if s.isNoExtPower() else 'test'
        s._dischargeReason.set(reason)
        s._dischargeStartTime.set(now)

        voltage = None
        try:
            voltage = s.hw.battery.voltage()
            s._dischargeStartVoltage.set(voltage)
        except BatteryVoltageError:
            pass
        s.dbw.addDischargeStatus(reason, voltage)


    def exitFromPowerLoss(s):
        now = int(time.time())
        s._dischargeStopTime.set(now)
        voltage = None
        try:
            voltage = s.hw.battery.voltage()
            s._dischargeStopVoltage.set(voltage)
        except BatteryVoltageError:
            pass
        s.dbw.updateDischargeEnd(voltage)


    def inputPowerEventHandler(s, state):
        print("inputPowerEventHandler state = %d" % state)
        with s._lock:
            if not state: # Power is absent
                Task.sleep(500)
                if s.charger.isStarted():
                    s.chargerStop()
                s.enterToPowerLoss()
                s.toAdmin('Пропало питание ИБП')
                return

            # Power resumed
            s.exitFromPowerLoss()
            s.toAdmin('питание ИБП востановлено')
            try:
                s.chargerStart(1, 'power_loss')
            except BatteryVoltageError:
                s.toAdmin('Не удалось запустить зарядку: нет информации о напряжении АКБ')
                s.chargerStop()


    def extPowerEventHandler(s, state):
        print("extPowerEventHandler state = %d" % state)
        if state:
            s.toAdmin('Внешнее питание восстановлено')
        else:
            s.toAdmin('Пропало внешнее питание')


    def mode(s):
        return s._mode.val


    def setMode(s, mode):
        print("setMode %s" % mode)
        s._mode.set(mode)


    def taskUps(s):
        with s._lock:
            voltage = None
            try:
                voltage = s.hw.battery.voltage()
            except BatteryVoltageError:
                s.noVoltage = True
                if s.charger.isStarted():
                    s.charger.pause()
                    s.toAdmin("Ошибка получения информации о напряжении на АКБ.\n" \
                                  "Контроль за АКБ утерян.")

            if s.noVoltage and voltage != None:
                s.noVoltage = False
                s.toAdmin("Информация о напряжении на АКБ получена %.2fv.\n" \
                              "Контроль за АКБ продолжается." % voltage)
                if s.mode() == 'charge':
                    s.charger.resume()

            if s.noVoltage:
                return

            if s.isDischarge() and s.mode() != 'discharge':
                s.enterToPowerLoss()
                s.toAdmin('Пропало питание ИБП')

            if s.mode() == 'waiting':
                return s.doWaiting(voltage)

            if s.mode() == 'discharge':
                return s.doDischarge(voltage)


    def doDischarge(s, voltage):
        if voltage >= 11.5:
            return

        print("voltage <= 11.5")
        s.toAdmin('Напряжение на АКБ снизилось до %.2fv' % voltage)
        s.dbw.updateDischargeEnd(voltage)
        s.exitFromPowerLoss()

        if s.isNoExtPower():
            s.toAdmin('Внешнее питание так и не появилось' \
                      'Skynet сворачивает свою деятельность и отключается.')
            try:
                s.hw.disableInputPower()
                s.hw.disableBatteryRelay()
            except IoError as e:
                s.toAdmin('Не удалось подготовить систему к отключению: %s' % e)
            exit(0)
            # TODO
            return

        s.printDischargeTestStatus()
        for i in range(3):
            try:
                s.hw.enableInputPower()
                break
            except IoError as e:
                s.toAdmin("Попытка %d: Не удалось включить " \
                          "внешнее питание: %s" % (i, e))
                Task.sleep(500)


    def doWaiting(s, voltage):
        if not s._automaticEnabled.val:
            return

        if voltage < 12.0:
            print("voltage < 12")
            return s.chargerStart(1, 'automatic')

        if voltage < 12.5:
            print("voltage < 12.5")
            return s.chargerStart(3, 'automatic')


    def isDischarge(s):
        return not s.hw.powerInUpsPort.cachedState() or not s.hw.powerExtPort.cachedState()


    def isNoExtPower(s):
        return not s.hw.powerExtPort.cachedState()


    def toAdmin(s, msg):
        s.tc.toAdmin("UPS: %s" % msg)


    def chargerStart(s, stageNum, reason=None):
        s.charger.start(stageNum, reason)
        s.setMode('charge')
        s.uiUpdater.call()


    def chargerStop(s):
        s.charger.stop()
        s.setMode('stopped')
        s.uiUpdater.call()


    def printDischargeTestStatus(s):
        duration = None
        if s._dischargeStartTime.val and s._dischargeStopTime.val:
            duration = s._dischargeStopTime.val - s._dischargeStartTime.val

        tgMsg = "Тест АКБ завершен.\n"
        if s._dischargeStartVoltage.val:
            tgMsg += "Начальное напряжение: %.2fv\n" % s._dischargeStartVoltage.val
        if s._dischargeStopVoltage.val:
            tgMsg += "Конечное напряжение: %.2fv\n" % s._dischargeStopVoltage.val
        if duration:
            tgMsg += "Время автономной работы: %s\n" % duration
        s.toAdmin(tgMsg)


    def uiUpdateHandler(s):
        now = int(time.time())

        data = {}
        try:
            data['ledPowerExtExist'] = s.hw.powerExtPort.cachedState()
        except IoPortCachedStateExpiredError:
            pass

        try:
            data['ledPowerInUps'] = s.hw.powerInUpsPort.cachedState()
        except IoPortCachedStateExpiredError:
            pass

        try:
            data['ledPowerOutUpsIsAbsent'] = not s.hw.powerOutUpsPort.cachedState()
        except IoPortCachedStateExpiredError:
            pass

        try:
            data['ledPower14vdcUpsAbsent'] = not s.hw.powerUps14vdcPort.cachedState()
        except IoPortCachedStateExpiredError:
            pass

        data['ledAutomaticCharhing'] = s._automaticEnabled.val


        data['ledCharging'] = False
        mode = s.mode()
        ups_state = mode
        if mode == 'charge':
            ups_state = "%s_%s" % (mode, s.chargerStage())
            data['ledCharging'] = True

        data['upsState'] = ups_state

        try:
            data['battVoltage'] = s.hw.battery.voltage()
        except BatteryVoltageError:
            pass

        try:
            data['chargeCurrent'] = s.hw.battery.chargerCurrent()
        except ChargeCurrentError:
            pass

        data['ledChargerEnPort'] = s.hw.enablePort.cachedState()
        data['ledHighCurrent'] = s.hw.highCurrentPort.cachedState()
        data['ledMiddleCurrent'] = s.hw.middleCurrentPort.cachedState()
        data['ledChargeDischarge'] = s.hw.chargeDischargePort.cachedState()
        data['ledBatteryRelayPort'] = s.hw.batteryRelayPort.cachedState()
        data['ledUpsBreakPowerPort'] = s.hw.upsBreakPowerPort.cachedState()

        if s.charger._chargingReason.val:
            data['chargingReason'] = s.charger._chargingReason.val
        if s.charger._chargerStartTime.val:
            data['chargerStartTime'] = s.charger._chargerStartTime.val
        if s.charger._chargerStopTime.val:
            data['chargerStopTime'] = s.charger._chargerStopTime.val
        if s.charger._chargeStartVoltage.val:
            data['chargeStartVoltage'] = s.charger._chargeStartVoltage.val

        totalDuration = 0
        for stage, _ in s.charger._chargeDates.items():
            if not s.charger._chargeDates[stage].val:
                continue
            end = now if not s.charger._chargerStopTime.val else s.charger._chargerStopTime.val
            duration = end - s.charger._chargeDates[stage].val
            data['chargeDuration_%s' % stage] = duration
            totalDuration += duration

        if totalDuration:
            data['chargeTotalDuration'] = totalDuration

        try:
            data['ledDischarging'] = s.isDischarge()
        except IoPortCachedStateExpiredError:
            pass

        if s._dischargeReason.val:
            data['dischargeReason'] = s._dischargeReason.val
        if s._dischargeStartTime.val:
            data['dischargeStartTime'] = s._dischargeStartTime.val
        if s._dischargeStopTime.val:
            data['dischargeStopTime'] = s._dischargeStopTime.val

        if s._dischargeStartVoltage.val:
            data['dischargeStartVoltage'] = s._dischargeStartVoltage.val

        if s._dischargeStopVoltage.val:
            data['dischargeStopVoltage'] = s._dischargeStopVoltage.val

        if s._dischargeStartTime.val:
            if s._dischargeStopTime.val:
                data['dischargeDuration'] = s._dischargeStopTime.val - s._dischargeStartTime.val
            else:
                data['dischargeDuration'] = now - s._dischargeStartTime.val

        s.skynet.emitEvent('ups', 'statusUpdate', data)


    def destroy(s):
        s.chargerStop()



    class Charger():
        def __init__(s, ups):
            s.ups = ups
            s.hw = ups.hw
            s.storage = ups.storage
            s.log = Syslog('Ups.Charger')
            s._task = None
            s._started = False

            s._chargerStage = s.storage.key('/charger/charger_stage', 1) # 1 to 3
            s._chargingReason = s.storage.key('/charger/reason', 'manual') # 'manual', 'automatic', 'power_loss'
            s._chargerStartTime = s.storage.key('/charger/start_time', 0)
            s._chargerStopTime = s.storage.key('/charger/stop_time', 0)
            s._chargeStartVoltage = s.storage.key('/charger/start_voltage', 0)
            s._chargerStatusId = s.storage.key('/charger/status_id', 0)
            s._chargerStartStageTime = s.storage.key('/charger/start_stage_time', 0)

            s._chargeDates = {}
            s._chargeDates['stage1'] = s.storage.key('/charger/dates/stage1', 0)
            s._chargeDates['stage2'] = s.storage.key('/charger/dates/stage2', 0)
            s._chargeDates['stage3'] = s.storage.key('/charger/dates/stage3', 0)

            s.hw.battery.subscribe('charger', s.voltageCb, 'voltage')


        def toAdmin(s, msg):
            s.ups.toAdmin("Charger: %s" % msg)


        def start(s, stageNum, reason=None):
            now = int(time.time())

            if not reason:
                reason = s._chargingReason.val

            try:
                voltage = s.voltage()
                s._chargeStartVoltage.set(voltage)
            except BatteryVoltageError:
                s._chargeStartVoltage.set(0)

            s._chargingReason.set(reason)
            s._chargerStartTime.set(now)
            s._chargerStopTime.set(0)

            for i, _ in s._chargeDates.items():
                s._chargeDates[i].set(0)

            s.startStage(stageNum)
            s.dbw.addChargeStatus(reason, stageNum, voltage)


        def stop(s):
            if not s.isStarted():
                return
            now = int(time.time())
            s.stopStage()
            s.hw.stopCharger()
            s._chargerStopTime.set(now)
            s.dbw.updateChargeStageDuration(s._chargerStage.val)
            s.dbw.updateChargeEndTime()
            s._started = False


        def isStarted(s):
            return s._started


        def pause(s):
            s.stopStage()


        def resume(s):
            s.startStage(s, s.stage())


        def isPaused(s):
            return s.isStageRunning()


        def voltageCb(s, voltage):
            if voltage >= 13.8:
                print("voltage >= 13.8")
                s.startStage(2)
                s.dbw.updateChargeStageDuration(1)


            if voltage >= 14.4:
                print("voltage >= 14.4")
                s.startStage(3)
                s.dbw.updateChargeStageDuration(2)


            if voltage >= 15.1:
                print("voltage >= 15.1")
                s.setMode('waiting')
                s.ups.toAdmin('Заряд окончен, напряжение на АКБ %.2fv' % voltage)
                s.stop()
                s.chargerUpdateResult()


        def voltage(s):
            return s.hw.battery.voltage()


        def stage(s):
            return s._chargerStage.val


        def startStage(s, stage):
            print("Charger start")
            now = int(time.time())

            voltageMsg = ""
            try:
                voltage = s.hw.battery.voltage()
                voltageMsg = ", напряжение на АКБ %.2fv" % voltage
            except BatteryVoltageError:
                pass

            if s._task:
                s._task.remove()
                s._task = None

            s._task = Task('charger_stage%s' % stage, s.task,
                                  s.taskExitHandler, True)

            if stage == 1:
                s.toAdmin('Включен заряд максимальным током %s' % voltageMsg)
            if stage == 2:
                s.toAdmin('Включен заряд средним током %s' % voltageMsg)
            if stage == 3:
                s.toAdmin('Включен заряд минимальным током %s' % voltageMsg)

            s._chargeDates[stage].set(now)
            s._chargerStartStageTime.set(now)
            s._chargerStage.set(stage)

            s._task.start()
            s._started = True


        def stopStage(s):
            print("Charger stopChargerStage")
            if s._task:
                s._task.remove()
                s._task = None


        def isStageRunning(s):
            return s._task != None


        def task(s):
            try:
                if s.stage() == 1:
                    print("Charge do stage1")
                    s.hw.setCurrentHigh()
                    s.hw.enableCharger()
                    while True:
                        s.hw.switchToCharge()
                        Task.sleep(30 * 1000)
                        s.hw.switchToDischarge()
                        Task.sleep(20 * 1000)

                if s.stage() == 2:
                    print("Charge do stage2")
                    s.hw.enableCharger()
                    s.hw.setCurrentMiddle()
                    while True:
                        s.hw.switchToCharge()
                        Task.sleep(20 * 1000)
                        s.hw.switchToDischarge()
                        Task.sleep(30 * 1000)

                if s.stage() == 3:
                    print("Charge do stage3")
                    s.hw.enableCharger()
                    s.hw.setCurrentLow()
                    while True:
                        s.hw.switchToCharge()
                        Task.sleep(20 * 1000)
                        s.hw.switchToDischarge()
                        Task.sleep(30 * 1000)

            except IoError as e:
                s.stop()
                s.toAdmin('Ошибка зарядки АКБ: %s' % e)


        def taskExitHandler(s):
            s._task = None
            try:
                s.hw.stopCharger()
            except IoError as e:
                s.toAdmin('Не удалось остановить зарядку АКБ: %s' % e)




    class Db():
        def __init__(s, ups):
            s.ups = ups
            s.db = ups.db
            s.log = Syslog('Ups.Db')


        def addChargeStatus(s, reason, startStage, startVoltage):
            try:
                id = s.db.insert('ups_charge',
                                   {'reason': reason,
                                    'start_stage': startStage,
                                    'start_voltage': startVoltage})
                s.ups._chargerStatusId.set(id)
            except DatabaseConnectorError as e:
                s.log.err('Can`t insert into ups_charge: %s' % e)
                s.ups.toAdmin('Ошибка добавления в таблицу ups_charge: %s' % e)


        def updateChargeStageDuration(s, stageNum):
            try:
                id = s.ups._chargerStatusId.val
                if not id:
                    id = s.chargeStatLastId()
                if not id:
                    s.log.err('Can`t update charger stage%d duration: ' \
                              'can`t obtain last id' % stageNum)
                    return

                if not s._chargerStartStageTime.val:
                    s.log.err('Can`t update charger stage%d duration: ' \
                              'chargerStartStageTime is zero' % stageNum)
                    return

                now = int(time.time())
                duration = now - s._chargerStartStageTime.val
                s.db.update('ups_charge', id, {'stage%d_duration' % stageNum: duration})
            except DatabaseConnectorError as e:
                s.log.err('Can`t update charge duration: %s' % e)
                s.ups.toAdmin('Ошибка обновления времени заряда ' \
                              'в таблице ups_charge: %s' % e)


        def updateChargeEndTime(s):
            now = int(time.time())
            try:
                id = s.ups._chargerStatusId.val
                if not id:
                    id = s.chargeStatLastId()
                if not id:
                    s.log.err('Can`t update charger end time: ' \
                              'can`t obtain lat id')
                    return

                s.db.update('ups_charge', id,
                             dataWithOutComma={'end_time': "FROM_UNIXTIME(%d)" % now})
            except DatabaseConnectorError as e:
                s.log.err('Can`t update charge end time: %s' % e)
                s.ups.toAdmin('Ошибка обновления времени завершения ' \
                              'заряда в таблице ups_charge: %s' % e)


        def chargeStatLastId(s):
            row = s.db.query('select id from ups_charge order by id desc limit 1')
            return row['id']


        def dischargeStatLastId(s):
            row = s.db.query('select id from ups_discharge order by id desc limit 1')
            return row['id']


        def addDischargeStatus(s, reason, startVoltage):
            try:
                id = s.db.insert('ups_discharge',
                                   {'reason': reason,
                                    'start_voltage': startVoltage if startVoltage else 0})
                s.ups._dischargeStatusId.set(id)
            except DatabaseConnectorError as e:
                s.log.err('Can`t insert into ups_discharge: %s' % e)
                s.ups.toAdmin('Ошибка добавления в таблицу ups_discharge: %s' % e)


        def updateDischargeEnd(s, voltage):
            now = int(time.time())
            try:
                id = s.ups._dischargeStatusId.val
                if not id:
                    id = s.dischargeStatLastId()
                if not id:
                    s.log.err('Can`t update discharge end time: ' \
                              'can`t obtain last id')
                    return

                s.db.update('ups_discharge', id,
                            {'end_voltage': voltage},
                            {'end_time': "FROM_UNIXTIME(%d)" % now})
            except DatabaseConnectorError as e:
                s.log.err('Can`t update discharge end time: %s' % e)
                s.ups.toAdmin('Ошибка обновления времени завершения ' \
                              'разряда в таблице ups_discharge: %s' % e)



    class Hw():
        def __init__(s, ups):
            s.log = Syslog('Ups.Hw')
            s.ups = ups
            s.io = ups.skynet.io
            s.enablePort = s.io.port('charger_en')
            s.chargeDischargePort = s.io.port('charge_discharge')
            s.highCurrentPort = s.io.port('charger_high')
            s.middleCurrentPort = s.io.port('charger_middle')

            s.powerExtPort = s.io.port('external_power')
            s.powerInUpsPort = s.io.port('ups_220vac')
            s.powerOutUpsPort = s.io.port('ups_250vdc')
            s.powerUps14vdcPort = s.io.port('ups_14vdc')

            s.batteryRelayPort = s.io.port('battery_relay')
            s.upsBreakPowerPort = s.io.port('ups_break_power')

            ports = [s.enablePort, s.chargeDischargePort, s.highCurrentPort,
                     s.middleCurrentPort, s.powerExtPort, s.powerInUpsPort,
                     s.powerOutUpsPort, s.powerUps14vdcPort, s.batteryRelayPort,
                     s.upsBreakPowerPort]

            s.subscribers = []

            s.powerInUpsPort.subscribe('Ups.Hw', s.inputPowerEventHandler)
            s.powerExtPort.subscribe('Ups.Hw', s.extPowerEventHandler)

            s.battery = Ups.Hw.Battery(s)
            for port in ports:
                port.subscribe('ups', lambda state: s.ups.uiUpdater.call())


        def subscribe(s, name, fn, eventSource):
            subscriber = Ups.Hw.Subscriber(s, name, fn, eventSource)
            s.subscribers.append(subscriber)


        def inputPowerEventHandler(s, state):
            for subscriber in subscribers:
                subscriber.call('inputUpsPower', state)


        def extPowerEventHandler(s, state):
            for subscriber in subscribers:
                subscriber.call('extPower', state)


        def enableInputPower(s):
            s.powerInUpsPort.down()


        def disableInputPower(s):
            s.powerInUpsPort.up()


        def disableBatteryRelay(s):
            s.batteryRelayPort.down()


        def enableCharger(s):
            s.enablePort.up()


        def disableCharger(s):
            s.enablePort.down()
            s.chargeDischargePort.down()


        def switchToCharge(s):
            s.chargeDischargePort.down()


        def switchToDischarge(s):
            s.chargeDischargePort.up()


        def setCurrentLow(s):
            s.highCurrentPort.down()
            s.middleCurrentPort.down()


        def setCurrentMiddle(s):
            s.highCurrentPort.down()
            s.middleCurrentPort.up()


        def setCurrentHigh(s):
            s.highCurrentPort.up()
            s.middleCurrentPort.down()


        def stopCharger(s):
            s.disableCharger()
            s.switchToCharge()
            s.setCurrentLow()


        class Subscriber():
            def __init__(s, hw, name, fn, eventSource):
                s.jw = hw
                s.name = name
                s.fn = fn
                s.eventSource = eventSource


            def call(s, eventType, arg):
                if eventType == s.eventSource:
                    s.fn(arg)


            def __repr__(s):
                return "Ups.Hw.Subscriber:%s" % s.name()



        class Battery():
            def __init__(s, hw):
                s.hw = hw
                s.ups = hw.ups
                s.log = Syslog('Ups.Hw.Battery')
                s.subscribers = []

                s._voltage = None
                s._chargeCurrent = None
                s._voltageUpdatedTime = 0
                s._chargerCurrentUpdatedTime = 0

                s.ups.skynet.registerEventSubscriber('Ups.Hw.Battery', s.eventHandler,
                                                     ('mbio', ), ('batteryStatus', ))


            def subscribe(s, name, fn, eventSource):
                subscriber = Ups.Hw.Battery.Subscriber(s, name, fn, eventSource)
                s.subscribers.append(subscriber)


            def toAdmin(s, msg):
                s.ups.toAdmin("Battery: %s" % msg)


            def eventHandler(s, source, type, data):
                try:
                    if data['io_name'] != 'mbio1':
                        return
                    now = int(time.time())

                    s._voltage = None
                    s._chargeCurrent = None
                    if 'voltage' in data:
                        s._voltage = data['voltage']
                        s._voltageUpdatedTime = now
                        for subscriber in s.subscribers:
                            subscriber.call('voltage', s._voltage)
                    if 'current' in data:
                        s._chargeCurrent = data['current']
                        s._chargerCurrentUpdatedTime = now
                        for subscriber in s.subscribers:
                            subscriber.call('chargerCurrent', s._chargeCurrent)

                except KeyError as e:
                    s.toAdmin("Event handler error: field %s is absent in 'batteryStatus' evType" % e)
                    return


            def voltage(s):
                now = int(time.time())
                if (now - s._voltageUpdatedTime) > 30:
                    raise BatteryVoltageError(s.log, "Battery information not available")
                if not s._voltage:
                    raise BatteryVoltageError(s.log, "Battery information not available")
                return s._voltage


            def chargerCurrent(s):
                now = int(time.time())
                if (now - s._chargerCurrentUpdatedTime) > 30:
                    raise ChargeCurrentError(s.log, "Charger current not available")
                if not s._chargeCurrent:
                    raise ChargeCurrentError(s.log, "Charger current not available")
                return s._chargeCurrent


            class Subscriber():
                def __init__(s, batt, name, fn, eventSource):
                    s.batt = batt
                    s.name = name
                    s.fn = fn
                    s.eventSource = eventSource


                def call(s, eventType, arg):
                    if eventType == s.eventSource:
                        s.fn(arg)


                def __repr__(s):
                    return "Ups.Hw.Battery.Subscriber:%s" % s.name()




    class HttpHandlers():
        def __init__(s, ups):
            s.ups = ups
            hs = ups.httpServer
            hs.setReqHandler("GET", "/ups/switch_automatic", s.switchAutomatic)

            hs.setReqHandler("GET", "/ups/start_charger", s.chargerStart)
            hs.setReqHandler("GET", "/ups/stop_charger", s.chargerStop)

            hs.setReqHandler("GET", "/ups/charger_hw_on", s.chargerHwOn)
            hs.setReqHandler("GET", "/ups/charger_hw_off", s.chargerHwOff)

            hs.setReqHandler("GET", "/ups/high_current_on", s.highCurrentOn)
            hs.setReqHandler("GET", "/ups/high_current_off", s.highCurrentOff)

            hs.setReqHandler("GET", "/ups/middle_current_on", s.middleCurrentOn)
            hs.setReqHandler("GET", "/ups/middle_current_off", s.middleCurrentOff)

            hs.setReqHandler("GET", "/ups/switch_to_charge", s.switchToCharge)
            hs.setReqHandler("GET", "/ups/switch_to_discharge", s.switchToDischarge)

            hs.setReqHandler("GET", "/ups/battery_relay_on", s.batteryRelayOn)
            hs.setReqHandler("GET", "/ups/battery_relay_off", s.batteryRelayOff)

            hs.setReqHandler("GET", "/ups/input_power_off", s.inputPowerOff)
            hs.setReqHandler("GET", "/ups/input_power_on", s.inputPowerOn)


        def switchAutomatic(s, args, body, attrs, conn):
            if s.ups._automaticEnabled.val:
                s.ups._automaticEnabled.set(False)
            else:
                s.ups._automaticEnabled.set(True)
            s.ups.uiUpdater.call()


        def chargerStart(s, args, body, attrs, conn):
            with s.ups._lock:
                if s.ups.isDischarge():
                    raise HttpHandlerError("Can't start charger: Input power has absent")
                try:
                    s.ups.chargerStart(1, 'manual')
                except BatteryVoltageError:
                    raise HttpHandlerError("Can't start charger: No battery voltage information")


        def chargerStop(s, args, body, attrs, conn):
            with s.ups._lock:
                if not s.ups.charger.isStarted():
                    raise HttpHandlerError("Charger is not started")
                s.ups.chargerStop()


        def chargerHwOn(s, args, body, attrs, conn):
            try:
                s.ups.hw.enablePort.up()
            except IoError as e:
                raise HttpHandlerError("Can't enable charger: %s" % e)


        def chargerHwOff(s, args, body, attrs, conn):
            try:
                s.ups.hw.enablePort.down()
            except IoError as e:
                raise HttpHandlerError("Can't disable charger: %s" % e)


        def highCurrentOn(s, args, body, attrs, conn):
            try:
                s.ups.hw.highCurrentPort.up()
            except IoError as e:
                raise HttpHandlerError("Can't upper io port high current: %s" % e)


        def highCurrentOff(s, args, body, attrs, conn):
            try:
                s.ups.hw.highCurrentPort.down()
            except IoError as e:
                raise HttpHandlerError("Can't lower io port high current: %s" % e)


        def middleCurrentOn(s, args, body, attrs, conn):
            try:
                s.ups.hw.middleCurrentPort.up()
            except IoError as e:
                raise HttpHandlerError("Can't upper io port middle current: %s" % e)


        def middleCurrentOff(s, args, body, attrs, conn):
            try:
                s.ups.hw.middleCurrentPort.down()
            except IoError as e:
                raise HttpHandlerError("Can't lower io port middle current: %s" % e)


        def switchToCharge(s, args, body, attrs, conn):
            try:
                s.ups.hw.chargeDischargePort.down()
            except IoError as e:
                raise HttpHandlerError("Can't switch to charge: %s" % e)


        def switchToDischarge(s, args, body, attrs, conn):
            try:
                s.ups.hw.chargeDischargePort.up()
            except IoError as e:
                raise HttpHandlerError("Can't switch to discharge: %s" % e)


        def batteryRelayOn(s, args, body, attrs, conn):
            try:
                s.ups.hw.batteryRelayPort.up()
            except IoError as e:
                raise HttpHandlerError("Can't enable battery relay: %s" % e)


        def batteryRelayOff(s, args, body, attrs, conn):
            try:
                s.ups.hw.batteryRelayPort.down()
            except IoError as e:
                raise HttpHandlerError("Can't disable battery relay: %s" % e)


        def inputPowerOff(s, args, body, attrs, conn):
            try:
                s.ups.hw.upsBreakPowerPort.up()
            except IoError as e:
                raise HttpHandlerError("Can't break ups input power: %s" % e)


        def inputPowerOn(s, args, body, attrs, conn):
            try:
                s.ups.hw.upsBreakPowerPort.down()
            except IoError as e:
                raise HttpHandlerError("Can't reestablish ups input power: %s" % e)




