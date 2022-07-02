from datetime import date
import requests, simplejson
from Exceptions import *
from HttpServer import *
from Skynet import *


class Boiler():
    def __init__(s, skynet):
        s.log = Syslog('Boiler')
        s.skynet = skynet
        s.conf = skynet.conf.boiler
        s.httpServer = skynet.httpServer
        s.db = skynet.db
        s.dbw = Boiler.Db(s, s.db)
        s.httpHandlers = Boiler.HttpHandlers(s, s.httpServer, s.dbw)


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
                    "Response for '%s' from boiler '%s' parse error: %s. Response: %s" % (
                            op, s.name, e, r.content)) from e
        except KeyError as e:
            raise BoilerError(s.log,
                    "Request '%s' to boiler return incorrect json: %s" % (
                            op, r.content)) from e


    def setTarget_t(s, t):
        s.send('boiler/set_target_t', {'t': t})


    def boilerEnable(s, args, body, attrs, conn):
        s.send('boiler/enable')


    def heaterEnable(s, args, body, attrs, conn):
        s.send('boiler/fun_heater_enable')


    def heaterDisable(s, args, body, attrs, conn):
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
            s.httpServer = httpServer
            s.httpServer.setReqHandler("GET", "/boiler/set_target_t",
                                        s.setTarget_tHandler, ('t', ))
            s.httpServer.setReqHandler("GET", "/boiler/boiler_start",
                                        s.boilerStartHandler)
            s.httpServer.setReqHandler("GET", "/boiler/heater_enable",
                                        s.heaterEnableHandler)
            s.httpServer.setReqHandler("GET", "/boiler/heater_disable",
                                        s.heaterDisableHandler)
            s.httpServer.setReqHandler("GET", "/boiler/request_fuel_compsumption_stat",
                                        s.reqFuelConsumptionStatHandler)


        def setTarget_tHandler(s, args, body, attrs, conn):
            try:
                s.boiler.setTarget_t(args['t'])
            except BoilerError as e:
                raise HttpHandlerError('Can`t set target temperature: %s' % e)



        def boilerStartHandler(s, args, body, attrs, conn):
            try:
                s.boiler.send('boiler/start')
            except BoilerError as e:
                raise HttpHandlerError('Can`t enable boiler: %s' % e)


        def heaterEnableHandler(s, args, body, attrs, conn):
            try:
                s.boiler.send('boiler/fun_heater_enable')
            except BoilerError as e:
                raise HttpHandlerError('Can`t enable heater: %s' % e)


        def heaterDisableHandler(s, args, body, attrs, conn):
            try:
                s.boiler.send('boiler/fun_heater_disable')
            except BoilerError as e:
                raise HttpHandlerError('Can`t disable heater: %s' % e)


        def reqFuelConsumptionStatHandler(s, args, body, attrs, conn):
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



