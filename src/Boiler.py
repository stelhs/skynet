from datetime import date
import requests, simplejson
from Exceptions import *
from HttpServer import *
from Skynet import *


class Boiler():
    def __init__(s, skynet):
        s.log = Syslog('Boiler')
        s.skynet = skynet
        s.tc = skynet.tc
        s.conf = skynet.conf.boiler
        s.httpServer = skynet.httpServer
        s.db = skynet.db
        s.dbw = Boiler.Db(s, s.db)
        s.httpHandlers = Boiler.HttpHandlers(s, s.httpServer, s.dbw)
        s.TgHandlers = Boiler.TgHandlers(s)


    def send(s, op, args = {}):
        url = "http://%s:%s/%s" % (s.conf['host'], s.conf['port'], op)
        try:
            r = requests.get(url = url, params = args)
            resp = r.json()
            if resp['status'] != 'ok' and resp['reason']:
                raise BoilerError(s.log,
                        "Request '%s' to boiler return response with error: %s" % (
                                op, resp['reason']))
            return resp
        except requests.RequestException as e:
            raise BoilerError(s.log,
                    "Request '%s' to bolier fails: %s" % (
                            op, e)) from e
        except simplejson.errors.JSONDecodeError as e:
            raise BoilerError(s.log,
                    "Response for '%s' from boiler parse error: %s. Response: %s" % (
                            op, e, r.content)) from e
        except KeyError as e:
            raise BoilerError(s.log,
                    "Request '%s' to boiler return incorrect json: %s" % (
                            op, r.content)) from e

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
                s.skynet.emitEvent('boiler', 'boilerFuelConsumption', listByYears)

            Task.asyncRunSingle("requestFuelConsumption", report)



    class TgHandlers():
        def __init__(s, boiler):
            s.boiler = boiler
            s.tc = boiler.tc

            s.tc.registerHandler('boiler', s.setFixed, 'w', ('??????',))
            s.tc.registerHandler('boiler', s.setT, 'w', ('???????????????? ??????????????????????', 'boiler set t'))


        def setFixed(s, arg, replyFn):
            fixedT = 17.0
            try:
                s.boiler.setTarget_t(fixedT)
            except AppError as e:
                return replyFn("???? ?????????????? ???????????????????? ??????????????????????: %s" % e)
            replyFn("?????????????????????? ?????????????????????? %.1f ????????????????" % fixedT)


        def setT(s, arg, replyFn):
            try:
                t = float(arg)
                s.boiler.setTarget_t(t)
            except ValueError as e:
                return replyFn("???? ?????????????? ???????????? ?????????? ?????????????????????? ???????????????????? ????????????????????: %s" % e)
            except AppError as e:
                return replyFn("???? ?????????????? ???????????????????? ??????????????????????: %s" % e)
            replyFn("?????????????????????? ?????????????????????? %.1f ????????????????" % t)


