from datetime import date
from Exceptions import *
from HttpServer import *
from Skynet import *
from HttpClient import *
from AveragerQueue import *


class Boiler():
    def __init__(s, skynet):
        s.log = Syslog('Boiler')
        s.skynet = skynet
        s.tc = skynet.tc
        s.ts = skynet.ts
        s.conf = skynet.conf.boiler
        s.httpServer = skynet.httpServer
        s.db = skynet.db
        s.dbw = Boiler.Db(s, s.db)
        s.httpHandlers = Boiler.HttpHandlers(s, s.httpServer, s.dbw)
        s.TgHandlers = Boiler.TgHandlers(s)

        skynet.registerEventSubscriber('Boiler', s.eventHandler,
                                        ('boiler', ), ('boilerState', ))
        s.httpClient = HttpClient('boiler', s.conf['host'], s.conf['port'])
        skynet.cron.register('boilerStat', ('0 0 9 * * *',)).addCb(s.cronStatHandler)
        s.termoStat = Boiler.TermoStat(s)


    def toAdmin(s, msg):
        s.tc.toAdmin("Boiler: %s" % msg)


    def eventHandler(s, source, type, data):
        termos = {}
        sevenSegs = {}

        if 'state' in data:
            s.skynet.emitEvent('boilerSkynet', 'statusBarsUpdate',
                               {'sbBolierState': data['state']})

        if 'target_t' in data:
            termos['ssBoilerTarget_t'] = round(data['target_t'], 1)

        if 'room_t' in data:
            termos['ssBoilerRoom_t'] = round(data['room_t'], 1)

        if 'boiler_box_t' in data:
            termos['ssBoilerBox_t'] = round(data['boiler_box_t'], 1)

        if 'boiler_box_t' in data:
            termos['ssBoilerBox_t'] = round(data['boiler_box_t'], 1)

        if 'boiler_t' in data:
            termos['ssBoilerWater_t'] = round(data['boiler_t'], 1)

        if 'return_t' in data:
            termos['ssBoilerRetWater_t'] = round(data['return_t'], 1)

        s.skynet.emitEvent('boilerSkynet', 'sevenSegsUpdate', termos)

        if 'ignition_counter' in data:
            sevenSegs['ssBoilerIgnitionCounter'] = data['ignition_counter']

        if 'fuel_consumption' in data:
            sevenSegs['ssBoilerFuelConsumption'] = round(data['fuel_consumption'], 1)

        s.skynet.emitEvent('boilerSkynet', 'sevenSegsUpdate', sevenSegs)



    def send(s, op, args = {}):
        try:
            return s.httpClient.reqGet(op, args)
        except HttpClient.Error as e:
            raise BoilerError(s.log, e) from e


    def setTarget_t(s, t):
        s.send('boiler/set_target_t', {'t': t})


    def start(s):
        s.send('boiler/start')


    def heaterEnable(s):
        s.send('boiler/fun_heater_enable')


    def heaterDisable(s):
        s.send('boiler/fun_heater_disable')


    def uiErr(s, msg):
        s.skynet.emitEvent('boiler', 'error', msg)


    def stat(s):
        return s.send('boiler/stat')


    def resetStat(s):
        s.send('boiler/reset_stat')


    def cronStatHandler(s, cronWorker=None):
        try:
            st = s.stat()
        except BoilerError as e:
            s.toAdmin('Ошибка получения статистики котла: %s' % e)
            return
        try:
            s.dbw.addDailyStat(st['burningTimeTotal'],
                               st['fuelConsumption'] * 1000,
                               st['ignitionCounter'],
                               s.termoStat.sensorOverageT('workshop_radiators'),
                               s.termoStat.sensorOverageT('workshop_inside1'),
                               s.termoStat.sensorOverageT('RP_top'))
            s.termoStat.reset()
        except DatabaseConnectorError as e:
            s.toAdmin('Не удалось сохранить статистику котла: %s' % e)
            return
        try:
            s.resetStat()
        except BoilerError as e:
            s.toAdmin('Ошибка сброса статистики кота: %s' % e)

        if st['ignitionCounter']:
            text = "Статистика по котлу:\n"
            text += "    Время работы котла: %s\n" % timeDurationStr(st['burningTimeTotal'])
            text += "    Количество запусков: %d\n" % st['ignitionCounter']
            text += "    Израсходовано топлива: %.1fл.\n" % st['fuelConsumption']
            s.toAdmin(text)



    def textStat(s):
        try:
            st = s.stat()
        except BoilerError as e:
            return "Ошибка при запросе статуса котла: %s\n" % e

        text = "Котёл:\n"
        text += "    Состояние: %s\n" % st['state']
        if 'stopReason' in st:
            text += "    Причина остановки: %s\n" % st['stopReason']
        text += "    Питание: %s\n" % ('присутсвует' if st['hwPowerState'] else 'отсутсвует')
        text += "    Давление: %s\n" % ('присутсвует' if st['pressureState'] else 'отсутсвует')
        text += "    Тепловентилятор: %s\n" % ('включён' if st['funHeaterState'] else 'отключён')
        text += "    Количество запусков: %s\n" % st['ignitionCounter']
        text += "    Израсходованно топлива: %.1f л\n" % st['fuelConsumption']

        if 'target_t' in st:
            text += "    Установленная температура: %.1f°\n" % st['target_t']
        if 'room_t' in st:
            text += "    Температура в мастерской: %.1f°\n" % st['room_t']
        if 'boiler_t' in st:
            text += "    Температура в котле: %.1f°\n" % st['boiler_t']
        if 'return_t' in st:
            text += "    Температура в радиаторах: %.1f°\n" % st['return_t']
        if 'overHeartingState' in st and st['overHeartingState']:
            text += "  Сработала защита по перегреву котла!\n"
        return text


    def __repr__(s):
        return s.textStat()



    class TermoStat():
        def __init__(s, boiler):
            ts = boiler.skynet.ts
            s._sensors = [Boiler.TermoStat.Sensor(ts, 'RP_top'),
                          Boiler.TermoStat.Sensor(ts, 'workshop_inside1'),
                          Boiler.TermoStat.Sensor(ts, 'workshop_radiators')]


        def reset(s):
            for sn in s._sensors:
                sn.reset()


        def sensorOverageT(s, name):
            for sn in s._sensors:
                if sn.name() == name:
                    return sn.overage()


        def __repr__(s):
            text = "Boiler.TermoStat:\n"
            for sn in s._sensors:
                text += "\t%s: %.2f\n" % (sn.name(), sn.overage())
            return text



        class Sensor():
            def __init__(s, ts, name):
                s.sn = ts.sensor(name)
                s.queue = AveragerQueue()
                s.sn.registerSubscriber('boiler', s.handler)


            def name(s):
                return s.sn.name()


            def handler(s, t):
                s.queue.push(t)


            def reset(s):
                s.queue.clear()


            def overage(s):
                return s.queue.round()


            def __repr__(s):
                return "Boiler.TermoStat.Sensor:%s" % s.name()




    class Db():
        def __init__(s, boiler, db):
            s.boiler = boiler
            s.db = db


        def fuelConsumptionMonthly(s, year, m):
            row = s.db.query("select sum(fuel_consumption) as sum " \
                             "from `boiler_statistics` " \
                             "WHERE year(created)=%d and month(created)=%d" % (year, m))
            if 'sum' not in row:
                return 0
            if row['sum'] == None:
                return 0
            return row['sum']


        def addDailyStat(s, burningTime, fuelConsumption,
                         ignitionCounter, retWaterT, roomT, outsideT):
            s.db.insert('boiler_statistics',
                        {'burning_time': burningTime,
                         'fuel_consumption': fuelConsumption,
                         'ignition_counter': ignitionCounter,
                         'return_water_t': retWaterT,
                         'room_t': roomT,
                         'outside_t': outsideT})




    class HttpHandlers():
        def __init__(s, boiler, httpServer, dbw):
            s.boiler = boiler
            s.skynet = boiler.skynet
            s.dbw = dbw
            s.regUiHandler('w', "GET", "/boiler/set_target_t", s.setTarget_tHandler, ('t', ))
            s.regUiHandler('w', "GET", "/boiler/boiler_start", s.boilerStartHandler)
            s.regUiHandler('w', "GET", "/boiler/heater_enable", s.heaterEnableHandler)
            s.regUiHandler('w', "GET", "/boiler/heater_disable", s.heaterDisableHandler)
            s.regUiHandler('r', "GET", "/boiler/request_fuel_compsumption_stat",
                                  s.reqFuelConsumptionStatHandler)


        def regUiHandler(s, permissionMode, method, url, handler,
                                requiredFields=[], retJson=True):
            s.skynet.ui.setReqHandler('boiler', permissionMode, method,
                                      url, handler, requiredFields, retJson)


        def setTarget_tHandler(s, args, conn):
            try:
                s.boiler.setTarget_t(args['t'])
            except BoilerError as e:
                raise HttpHandlerError('Can`t set target temperature: %s' % e)


        def boilerStartHandler(s, args, conn):
            try:
                s.boiler.start()
            except BoilerError as e:
                raise HttpHandlerError('Can`t enable boiler: %s' % e)


        def heaterEnableHandler(s, args, conn):
            try:
                s.boiler.heaterEnable()
            except BoilerError as e:
                raise HttpHandlerError('Can`t enable heater: %s' % e)


        def heaterDisableHandler(s, args, conn):
            try:
                s.boiler.heaterDisable()
            except BoilerError as e:
                raise HttpHandlerError('Can`t disable heater: %s' % e)


        def reqFuelConsumptionStatHandler(s, args, conn):
            def report():
                endYear = date.today().year;
                startYear = endYear - 5;

                listByYears = []
                for year in range(startYear + 1, endYear + 1):
                    listByMonths = []
                    yearSum = 0
                    for m in range(1, 12):
                        try:
                            monthlySum = s.dbw.fuelConsumptionMonthly(year, m)
                        except DatabaseConnectorError as e:
                            s.boiler.uiErr("Calculating total fuel consumption for %d.%d failed: " \
                                           "Database error: %s" % (m, year, e))
                            return

                        yearSum += monthlySum
                        listByMonths.append({'month': m,
                                             'liters': float(round(monthlySum / 1000, 1))})

                    if yearSum:
                        listByYears.append({'year': year,
                                            'months': listByMonths,
                                            'total': float(round(yearSum / 1000, 1))})
                s.skynet.emitEvent('boilerSkynet', 'boilerFuelConsumption', listByYears)

            Task.asyncRunSingle("requestFuelConsumption", report)



    class TgHandlers():
        def __init__(s, boiler):
            s.boiler = boiler
            s.tc = boiler.tc
            s.ts = boiler.ts

            s.tc.registerHandler('boiler', s.setFixed, 'w', ('еду',))
            s.tc.registerHandler('boiler', s.setT, 'w', ('установи температуру', 'boiler set t'))
            s.tc.registerHandler('boiler', s.start, 'w', ('включи котёл', ))


        def setFixed(s, arg, replyFn):
            s.setT(17.0, replyFn)


        def setT(s, arg, replyFn):
            msg = ""
            try:
                t = float(arg)
                s.boiler.setTarget_t(t)
                msg += "Установлена температура %.1f градусов\n" % t
            except ValueError as e:
                return replyFn("Не удалось понять какую температуру необходимо установить: %s" % e)
            except AppError as e:
                return replyFn("Не удалось установить температуру: %s" % e)

            try:
                sn = s.ts.sensor('workshop_inside1')
                msg += "Текущая температура в мастерской: %.1f градусов\n" % sn.t()
            except AppError as e:
                return replyFn("Не удалось получить текущую температуру: %s" % e)
            try:
                stat = s.boiler.stat()
                if stat['state'] == 'STOPPED':
                    msg += "Однако котёл выключен."
                    if stat['stopReason']:
                        msg += "Причина остановки: %s" % stat['stopReason']
                    msg += "\n"
            except AppError as e:
                return replyFn("Не удалось получить статус котла: %s" % e)
            replyFn(msg)


        def start(s, arg, replyFn):
            try:
                s.boiler.start()
            except AppError as e:
                return replyFn("Не удалось включить котёл: %s" % e)
            replyFn("Котёл включается")



