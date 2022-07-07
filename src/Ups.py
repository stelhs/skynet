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
        s.upsTask = Task.setPeriodic('ups', 1000, s.doControlUps)

        s.storage = Storage('ups.json')
        s._mode = s.storage.key('/mode', 'charge') # 'charge', 'discharge', 'waiting', 'stopped'
        s._automaticEnabled = s.storage.key('/charger/automatic_enabled', True)


        s.dischargeReason = s.storage.key('/discharge/reason', None) # 'test', 'power_lost'
        s.dischargeStartTime = s.storage.key('/discharge/start_time', 0)
        s.dischargeStopTime = s.storage.key('/discharge/stop_time', 0)
        s.dischargeStartVoltage = s.storage.key('/discharge/start_voltage', None)
        s.dischargeStopVoltage = s.storage.key('/discharge/stop_voltage', None)
        s.dischargeStatusId = 0
        s.dischargeFinished = False

        s.hw = Ups.Hw(s)
        s.hw.subscribe('ups', s.inputPowerEventHandler, 'inputUpsPower')
        s.hw.subscribe('ups', s.extPowerEventHandler, 'extPower')

        s.charger = Ups.Charger(s)

        s.uiUpdater = s.skynet.periodicNotifier.register("ups", s.uiUpdateHandler, 2000)
        s.init()
        s.httpHandlers = Ups.HttpHandlers(s)


    def init(s):
        with s._lock:
            if s.isDischarge():
                s.enterToPowerLoss()

            if s.mode() == 'discharge' and not s.isDischarge():
                s.chargerStart(1)
                return

            if s.mode() == 'charge':
                s.noVoltage = True


    def enterToPowerLoss(s):
        now = int(time.time())
        s.setMode('discharge')
        reason = 'power_lost' if s.isNoExtPower() else 'test'
        s.dischargeReason.set(reason)
        s.dischargeStartTime.set(now)
        s.dischargeStopTime.set(0)
        s.dischargeStartVoltage.set(0)
        s.uiUpdater.call()

        voltage = None
        try:
            voltage = s.hw.battery.voltage()
            s.dischargeStartVoltage.set(voltage)
        except BatteryVoltageError:
            pass
        s.dbw.addDischargeStatus(reason, voltage)


    def exitFromPowerLoss(s):
        now = int(time.time())
        s.dischargeStopTime.set(now)
        voltage = None
        try:
            voltage = s.hw.battery.voltage()
            s.dischargeStopVoltage.set(voltage)
        except BatteryVoltageError:
            pass
        s.dbw.updateDischargeEnd(voltage)
        s.uiUpdater.call()


    def inputPowerEventHandler(s, state):
        with s._lock:
            if not state: # Power is absent
                if s.mode() == 'discharge':
                    return
                s.log.info('UPS input power is lost')
                Task.sleep(500)
                if s.charger.isStarted():
                    s.chargerStop()
                s.enterToPowerLoss()
                s.toAdmin('Пропало питание ИБП')
                return

            # Power resumed
            if s.mode() != 'discharge':
                return
            s.log.info('UPS input power is restored')
            s.exitFromPowerLoss()
            s.toAdmin('питание ИБП востановлено')
            try:
                s.chargerStart(1, 'power_lost')
            except BatteryVoltageError:
                s.log.err('Can`t start charger: no battery voltage information')
                s.toAdmin('Не удалось запустить зарядку: нет информации о напряжении АКБ')
                s.chargerStop()


    def extPowerEventHandler(s, state):
        with s._lock:
            if not state: # Power is absent
                if s.mode() == 'discharge':
                    return
                Task.sleep(500)
                if s.charger.isStarted():
                    s.chargerStop()
                s.enterToPowerLoss()
                s.log.info('External power is lost')
                s.toAdmin('Пропало внешнее питание')
                return

            # Power resumed
            if s.mode() != 'discharge':
                return
            s.exitFromPowerLoss()
            s.log.info('External power is restored')
            s.toAdmin('Внешнее питание восстановлено')
            try:
                s.chargerStart(1, 'power_lost')
            except BatteryVoltageError:
                s.log.err('Can`t start charger: no battery voltage information')
                s.toAdmin('Не удалось запустить зарядку: нет информации о напряжении АКБ')
                s.chargerStop()


    def mode(s):
        return s._mode.val


    def setMode(s, mode):
        s._mode.set(mode)


    def doControlUps(s):
        with s._lock:
            s.doCheckUpsHw()

            voltage = None
            try:
                voltage = s.hw.battery.voltage()
            except BatteryVoltageError:
                if s.noVoltage:
                    return
                s.noVoltage = True
                if s.charger.isStarted():
                    s.charger.pause()
                    s.log.err('Battery voltage error. Charger is paused')
                    s.toAdmin("Ошибка получения информации о напряжении на АКБ.\n" \
                                  "Контроль за АКБ утерян.")

            if s.noVoltage and voltage != None:
                s.noVoltage = False
                s.log.info('Battery voltage restored. Charger is resumed')
                s.toAdmin("Информация о напряжении на АКБ получена %.2fv.\n" \
                              "Контроль за АКБ продолжается." % voltage)
                if s.mode() == 'charge':
                    if  s.charger.isStarted():
                        s.charger.resume()
                    else:
                        s.charger.start(1, 'automatic')

            if s.noVoltage:
                return

            if s.isDischarge() and s.mode() != 'discharge':
                s.enterToPowerLoss()
                s.log.info('UPS input power is lost')
                s.toAdmin('Пропало питание ИБП')

            if s.mode() == 'waiting':
                return s.doWaiting(voltage)

            if s.mode() == 'discharge':
                return s.doDischarge(voltage)


    def doCheckUpsHw(s):
        if not s.hw.powerOutUpsPort.cachedState():
            s.log.err('250VDC Error')
            s.toAdmin("Нет выходного питания бесперебойника 250vdc")

        if not s.hw.powerUps14vdcPort.cachedState():
            s.log.err('14VDC Error')
            s.toAdmin("Нет внутреннего питания бесперебойника 14vdc")


    def doDischarge(s, voltage):
        if voltage >= 11.5:
            s.dischargeFinished = False
            return
        if s.dischargeFinished:
            return
        s.dischargeFinished = True

        s.log.info('Battery voltage decreased bellow 15.4v: voltage: %.2fv' % voltage)
        s.toAdmin('Напряжение на АКБ снизилось до %.2fv' % voltage)
        s.dbw.updateDischargeEnd(voltage)
        s.exitFromPowerLoss()

        if s.isNoExtPower():
            s.log.info('External power lost. Goodby')
            s.toAdmin('Внешнее питание так и не появилось' \
                      'Skynet сворачивает свою деятельность и отключается.')
            try:
                s.hw.disableInputPower()
                s.hw.turnOffBatteryRelay()
            except IoError as e:
                s.toAdmin('Не удалось подготовить систему к отключению: %s' % e)
            os.system("halt")
            return

        s.printDischargeTestStatus()
        for i in range(3):
            try:
                s.hw.enableInputPower()
                break
            except IoError as e:
                s.log.err('Can`t enable UPS input power: %s' % e)
                s.toAdmin("Попытка %d: Не удалось включить " \
                          "внешнее питание: %s" % (i, e))
                Task.sleep(500)


    def doWaiting(s, voltage):
        if not s._automaticEnabled.val:
            return

        if voltage < 12.0:
            return s.chargerStart(1, 'automatic')

        if voltage < 12.5:
            return s.chargerStart(3, 'automatic')


    def isDischarge(s):
        try:
            if not s.hw.powerExtPort.cachedState():
                return True
            if not s.hw.powerInUpsPort.cachedState():
                return True
            return False
        except IoPortCachedStateExpiredError:
            return False


    def isNoExtPower(s):
        try:
            return not s.hw.powerExtPort.cachedState()
        except IoPortCachedStateExpiredError:
            return False


    def toAdmin(s, msg):
        s.tc.toAdmin("UPS: %s" % msg)


    def chargerStart(s, stageNum, reason=None):
        s.dischargeFinished = False
        s.charger.start(stageNum, reason)
        s.setMode('charge')
        s.uiUpdater.call()


    def chargerStop(s):
        s.charger.stop()
        s.setMode('stopped')
        s.uiUpdater.call()


    def printDischargeTestStatus(s):
        duration = None
        if s.dischargeStartTime.val and s.dischargeStopTime.val:
            duration = s.dischargeStopTime.val - s.dischargeStartTime.val

        tgMsg = "Тест АКБ завершен.\n"
        if s.dischargeStartVoltage.val:
            tgMsg += "Начальное напряжение: %.2fv\n" % s.dischargeStartVoltage.val
        if s.dischargeStopVoltage.val:
            tgMsg += "Конечное напряжение: %.2fv\n" % s.dischargeStopVoltage.val
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
            ups_state = "%s_%s" % (mode, s.charger.stage())
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

        try:
            data['ledChargerEnPort'] = s.hw.enablePort.cachedState()
        except IoPortCachedStateExpiredError:
            pass

        try:
            data['ledHighCurrent'] = s.hw.highCurrentPort.cachedState()
        except IoPortCachedStateExpiredError:
            pass

        try:
            data['ledMiddleCurrent'] = s.hw.middleCurrentPort.cachedState()
        except IoPortCachedStateExpiredError:
            pass

        try:
            data['ledChargeDischarge'] = s.hw.chargeDischargePort.cachedState()
        except IoPortCachedStateExpiredError:
            pass

        try:
            data['ledBatteryRelayPort'] = s.hw.batteryRelayPort.cachedState()
        except IoPortCachedStateExpiredError:
            pass

        try:
            data['ledUpsBreakPowerPort'] = s.hw.upsBreakPowerPort.cachedState()
        except IoPortCachedStateExpiredError:
            pass

        if s.charger.chargingReason.val:
            data['chargingReason'] = s.charger.chargingReason.val
        if s.charger.startTime.val:
            data['chargerStartTime'] = timeDateToStr(s.charger.startTime.val)
        if s.charger.stopTime.val:
            data['chargerStopTime'] = timeDateToStr(s.charger.stopTime.val)
        if s.charger.startVoltage.val:
            data['chargeStartVoltage'] = s.charger.startVoltage.val

        totalDuration = 0
        for stage, _ in s.charger.chargeDates.items():
            if not s.charger.chargeDates[stage].val:
                continue
            duration = s.charger.stageDuration(stage)
            data['chargeDuration_stage%s' % stage] = timeDurationStr(duration)
            totalDuration += duration

        if totalDuration:
            data['chargeTotalDuration'] = timeDurationStr(totalDuration)

        try:
            data['ledDischarging'] = s.isDischarge()
        except IoPortCachedStateExpiredError:
            pass

        if s.dischargeReason.val:
            data['dischargeReason'] = s.dischargeReason.val
        if s.dischargeStartTime.val:
            data['dischargeStartTime'] = timeDateToStr(s.dischargeStartTime.val)
        if s.dischargeStopTime.val:
            data['dischargeStopTime'] = timeDateToStr(s.dischargeStopTime.val)

        if s.dischargeStartVoltage.val:
            data['dischargeStartVoltage'] = s.dischargeStartVoltage.val

        if s.dischargeStopVoltage.val:
            data['dischargeStopVoltage'] = s.dischargeStopVoltage.val

        if s.dischargeStartTime.val:
            if s.dischargeStopTime.val:
                data['dischargeDuration'] = timeDurationStr(s.dischargeStopTime.val - s.dischargeStartTime.val)
            else:
                data['dischargeDuration'] = timeDurationStr(now - s.dischargeStartTime.val)

        s.skynet.emitEvent('ups', 'statusUpdate', data)


    def destroy(s):
        s.upsTask.remove()
        print("destroy Ups")
        with s._lock:
            try:
                s.charger.stop()
                s.charger.destroy()
            except AppError as e:
                msg = 'Charger stop/destroy error: %s' % e
                s.log.err(msg)
                print(msg)



    class Charger():
        def __init__(s, ups):
            s.ups = ups
            s.hw = ups.hw
            s.dbw = ups.dbw
            s.storage = ups.storage
            s.log = Syslog('Ups.Charger')
            s._task = None
            s._started = False

            s.stageNum = s.storage.key('/charger/charger_stage', 1) # 1 to 3
            s.chargingReason = s.storage.key('/charger/reason', 'manual') # 'manual', 'automatic', 'power_lost'
            s.startTime = s.storage.key('/charger/start_time', 0)
            s.stopTime = s.storage.key('/charger/stop_time', 0)
            s.startVoltage = s.storage.key('/charger/start_voltage', 0)
            s.dbStatusId = 0
            s.startStageTime = s.storage.key('/charger/start_stage_time', 0)

            s.chargeDates = {}
            s.chargeDates[1] = s.storage.key('/charger/dates/stage1', 0)
            s.chargeDates[2] = s.storage.key('/charger/dates/stage2', 0)
            s.chargeDates[3] = s.storage.key('/charger/dates/stage3', 0)

            s.hw.battery.subscribe('charger', s.voltageCb, 'voltage')


        def toAdmin(s, msg):
            s.ups.toAdmin("Charger: %s" % msg)


        def start(s, stageNum, reason=None):
            now = int(time.time())
            if not reason:
                reason = s.chargingReason.val

            voltage = None
            try:
                voltage = s.voltage()
                s.startVoltage.set(voltage)
            except BatteryVoltageError:
                s.startVoltage.set(0)

            s.chargingReason.set(reason)
            s.startTime.set(now)
            s.stopTime.set(0)

            for i, _ in s.chargeDates.items():
                s.chargeDates[i].set(0)

            s.log.info('Charger start from stage %d' % stageNum)
            s.startStage(stageNum)
            s.dbw.addChargeStatus(reason, stageNum, voltage)


        def stop(s):
            if not s.isStarted():
                return
            now = int(time.time())
            s.stopStage()
            s.hw.stopCharger()
            s.stopTime.set(now)
            s.dbw.updateChargeStageDuration(s.stageNum.val)
            s.dbw.updateChargeEndTime()
            s._started = False
            s.log.info('Charger stop')


        def isStarted(s):
            return s._started


        def pause(s):
            s.stopStage()


        def resume(s):
            s.startStage(s.stage())


        def voltageCb(s, voltage):
            if not s.isStarted():
                return

            if s.stage() == 1 and voltage >= 13.8:
                s.startStage(2)
                s.dbw.updateChargeStageDuration(1)


            if s.stage() == 2 and voltage >= 14.4:
                s.startStage(3)
                s.dbw.updateChargeStageDuration(2)


            if s.stage() == 3 and voltage >= 15.1:
                s.ups.setMode('waiting')
                s.log.info('Charger finished')
                s.ups.toAdmin('Заряд окончен, напряжение на АКБ %.2fv' % voltage)
                s.stop()


        def voltage(s):
            return s.hw.battery.voltage()


        def stage(s):
            return s.stageNum.val


        def startStage(s, stage):
            now = int(time.time())
            s.log.info('Start stage %d' % stage)

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

            s.chargeDates[stage].set(now)
            s.startStageTime.set(now)
            s.stageNum.set(stage)

            s._task.start()
            s._started = True


        def stopStage(s):
            if s._task:
                s._task.remove()
                s._task = None


        def isStageRunning(s):
            return s._task != None


        def task(s):
            try:
                if s.stage() == 1:
                    s.hw.setCurrentHigh()
                    s.hw.enableCharger()
                    while True:
                        s.hw.switchToCharge()
                        Task.sleep(30 * 1000)
                        s.hw.switchToDischarge()
                        Task.sleep(20 * 1000)

                if s.stage() == 2:
                    s.hw.enableCharger()
                    s.hw.setCurrentMiddle()
                    while True:
                        s.hw.switchToCharge()
                        Task.sleep(20 * 1000)
                        s.hw.switchToDischarge()
                        Task.sleep(30 * 1000)

                if s.stage() == 3:
                    s.hw.enableCharger()
                    s.hw.setCurrentLow()
                    while True:
                        s.hw.switchToCharge()
                        Task.sleep(20 * 1000)
                        s.hw.switchToDischarge()
                        Task.sleep(30 * 1000)

            except IoError as e:
                s.stop()
                s.log.err('Charger error: %s' % e)
                s.toAdmin('Ошибка зарядки АКБ: %s' % e)


        def taskExitHandler(s):
            s._task = None
            try:
                s.hw.stopCharger()
            except IoError as e:
                s.log.err('Can`t stop charger: %s' % e)
                s.toAdmin('Не удалось остановить зарядку АКБ: %s' % e)


        def stageDuration(s, stageNum):
            now = int(time.time())
            if stageNum == 1:
                if not s.chargeDates[1].val:
                    return None
                if s.chargeDates[2].val:
                    return s.chargeDates[2].val - s.chargeDates[1].val
                if s.stopTime.val:
                    return s.stopTime.val - s.chargeDates[1].val
                return now - s.chargeDates[1].val

            if stageNum == 2:
                if not s.chargeDates[2].val:
                    return None
                if s.chargeDates[3].val:
                    return s.chargeDates[3].val - s.chargeDates[2].val
                if s.stopTime.val:
                    return s.stopTime.val - s.chargeDates[2].val
                return now - s.chargeDates[2].val

            if stageNum == 3:
                if not s.chargeDates[3].val:
                    return None
                if not s.stopTime.val:
                    return now - s.chargeDates[3].val
                return s.stopTime.val - s.chargeDates[3].val


        def destroy(s):
            if s._task:
                s._task.remove()
            s.storage.destroy()



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
                s.ups.charger.dbStatusId = id
            except DatabaseConnectorError as e:
                s.log.err('Can`t insert into ups_charge: %s' % e)
                s.ups.toAdmin('Ошибка добавления в таблицу ups_charge: %s' % e)


        def updateChargeStageDuration(s, stageNum):
            try:
                id = s.ups.charger.dbStatusId
                if not id:
                    id = s.chargeStatLastId()
                if not id:
                    s.log.err('Can`t update charger stage%d duration: ' \
                              'can`t obtain last id' % stageNum)
                    return

                if not s.ups.charger.startStageTime.val:
                    s.log.err('Can`t update charger stage%d duration: ' \
                              'startStageTime is zero' % stageNum)
                    return

                now = int(time.time())
                duration = s.ups.charger.stageDuration(stageNum)
                s.db.update('ups_charge', id, {'stage%d_duration' % stageNum: duration})
            except DatabaseConnectorError as e:
                s.log.err('Can`t update charge duration: %s' % e)
                s.ups.toAdmin('Ошибка обновления времени заряда ' \
                              'в таблице ups_charge: %s' % e)


        def updateChargeEndTime(s):
            now = int(time.time())
            try:
                id = s.ups.charger.dbStatusId
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
                s.ups.dischargeStatusId = id
            except DatabaseConnectorError as e:
                s.log.err('Can`t insert into ups_discharge: %s' % e)
                s.ups.toAdmin('Ошибка добавления в таблицу ups_discharge: %s' % e)


        def updateDischargeEnd(s, voltage):
            now = int(time.time())
            try:
                id = s.ups.dischargeStatusId
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
            s._lock = threading.Lock()
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
            for subscriber in s.subscribers:
                subscriber.call('inputUpsPower', state)


        def extPowerEventHandler(s, state):
            for subscriber in s.subscribers:
                subscriber.call('extPower', state)


        def enableInputPower(s):
            with s._lock:
                s.upsBreakPowerPort.down()


        def disableInputPower(s):
            with s._lock:
                s.upsBreakPowerPort.up()


        def turnOffBatteryRelay(s):
            with s._lock:
                s.batteryRelayPort.up()


        def enableCharger(s):
            with s._lock:
                s.enablePort.up()
                s.batteryRelayPort.down()


        def switchToCharge(s):
            with s._lock:
                s.chargeDischargePort.down()


        def switchToDischarge(s):
            with s._lock:
                s.chargeDischargePort.up()


        def setCurrentLow(s):
            with s._lock:
                s.highCurrentPort.down()
                s.middleCurrentPort.down()


        def setCurrentMiddle(s):
            with s._lock:
                s.highCurrentPort.down()
                s.middleCurrentPort.up()


        def setCurrentHigh(s):
            with s._lock:
                s.highCurrentPort.up()
                s.middleCurrentPort.down()

        def stopCharger(s):
            with s._lock:
                s.enablePort.down()
                s.chargeDischargePort.down()
                s.chargeDischargePort.down()
                s.highCurrentPort.down()
                s.middleCurrentPort.down()


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
                    err = "Event handler error: field %s is absent in 'batteryStatus' evType" % e
                    s.log.err(err)
                    s.toAdmin(err)
                    return


            def voltage(s):
                now = int(time.time())
                if (now - s._voltageUpdatedTime) > 10:
                    raise BatteryVoltageError(s.log, "Battery information not available")
                if not s._voltage:
                    raise BatteryVoltageError(s.log, "Battery information not available")
                return s._voltage


            def chargerCurrent(s):
                now = int(time.time())
                if (now - s._chargerCurrentUpdatedTime) > 10:
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
            s.skynet = ups.skynet
            s.regUiHandler('w', "GET", "/ups/switch_automatic", s.switchAutomatic)

            s.regUiHandler('w', "GET", "/ups/start_charger", s.chargerStart)
            s.regUiHandler('w', "GET", "/ups/stop_charger", s.chargerStop)

            s.regUiHandler('w', "GET", "/ups/charger_hw_on", s.chargerHwOn)
            s.regUiHandler('w', "GET", "/ups/charger_hw_off", s.chargerHwOff)

            s.regUiHandler('w', "GET", "/ups/high_current_on", s.highCurrentOn)
            s.regUiHandler('w', "GET", "/ups/high_current_off", s.highCurrentOff)

            s.regUiHandler('w', "GET", "/ups/middle_current_on", s.middleCurrentOn)
            s.regUiHandler('w', "GET", "/ups/middle_current_off", s.middleCurrentOff)

            s.regUiHandler('w', "GET", "/ups/switch_to_charge", s.switchToCharge)
            s.regUiHandler('w', "GET", "/ups/switch_to_discharge", s.switchToDischarge)

            s.regUiHandler('w', "GET", "/ups/battery_relay_on", s.batteryRelayOn)
            s.regUiHandler('w', "GET", "/ups/battery_relay_off", s.batteryRelayOff)

            s.regUiHandler('w', "GET", "/ups/input_power_off", s.inputPowerOff)
            s.regUiHandler('w', "GET", "/ups/input_power_on", s.inputPowerOn)


        def regUiHandler(s, permissionMode, method, url, handler,
                                requiredFields=[], retJson=True):
            s.skynet.ui.setReqHandler('ups', permissionMode, method,
                                       url, handler, requiredFields, retJson)


        def switchAutomatic(s, args, conn):
            if s.ups._automaticEnabled.val:
                s.ups._automaticEnabled.set(False)
            else:
                s.ups._automaticEnabled.set(True)
            s.ups.uiUpdater.call()


        def chargerStart(s, args, conn):
            with s.ups._lock:
                if s.ups.isDischarge():
                    raise HttpHandlerError("Can't start charger: Input power has absent")
                try:
                    s.ups.chargerStart(1, 'manual')
                except AppError as e:
                    raise HttpHandlerError("Can't start charger: %s" % e)


        def chargerStop(s, args, conn):
            with s.ups._lock:
                if not s.ups.charger.isStarted():
                    raise HttpHandlerError("Charger is not started")
                try:
                    s.ups.chargerStop()
                except AppError as e:
                    raise HttpHandlerError("Can't stop charger: %s" % e)



        def chargerHwOn(s, args, conn):
            try:
                s.ups.hw.enablePort.up()
            except IoError as e:
                raise HttpHandlerError("Can't enable charger: %s" % e)


        def chargerHwOff(s, args, conn):
            try:
                s.ups.hw.enablePort.down()
            except IoError as e:
                raise HttpHandlerError("Can't disable charger: %s" % e)


        def highCurrentOn(s, args, conn):
            try:
                s.ups.hw.highCurrentPort.up()
            except IoError as e:
                raise HttpHandlerError("Can't upper io port high current: %s" % e)


        def highCurrentOff(s, args, conn):
            try:
                s.ups.hw.highCurrentPort.down()
            except IoError as e:
                raise HttpHandlerError("Can't lower io port high current: %s" % e)


        def middleCurrentOn(s, args, conn):
            try:
                s.ups.hw.middleCurrentPort.up()
            except IoError as e:
                raise HttpHandlerError("Can't upper io port middle current: %s" % e)


        def middleCurrentOff(s, args, conn):
            try:
                s.ups.hw.middleCurrentPort.down()
            except IoError as e:
                raise HttpHandlerError("Can't lower io port middle current: %s" % e)


        def switchToCharge(s, args, conn):
            try:
                s.ups.hw.chargeDischargePort.down()
            except IoError as e:
                raise HttpHandlerError("Can't switch to charge: %s" % e)


        def switchToDischarge(s, args, conn):
            try:
                s.ups.hw.chargeDischargePort.up()
            except IoError as e:
                raise HttpHandlerError("Can't switch to discharge: %s" % e)


        def batteryRelayOn(s, args, conn):
            try:
                s.ups.hw.batteryRelayPort.up()
            except IoError as e:
                raise HttpHandlerError("Can't enable battery relay: %s" % e)


        def batteryRelayOff(s, args, conn):
            try:
                s.ups.hw.batteryRelayPort.down()
            except IoError as e:
                raise HttpHandlerError("Can't disable battery relay: %s" % e)


        def inputPowerOff(s, args, conn):
            try:
                s.ups.hw.upsBreakPowerPort.up()
            except IoError as e:
                raise HttpHandlerError("Can't break ups input power: %s" % e)


        def inputPowerOn(s, args, conn):
            try:
                s.ups.hw.upsBreakPowerPort.down()
            except IoError as e:
                raise HttpHandlerError("Can't reestablish ups input power: %s" % e)



