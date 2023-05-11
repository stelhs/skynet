import json
from HttpClient import *
from Exceptions import *
from Syslog import *


class GsmModem():
    def __init__(s, skynet):
        s.skynet = skynet
        s.tc = skynet.tc
        s.log = Syslog('GsmModem')
        skynet.registerEventSubscriber('GsmModem', s.smsListener, ('mbio', ), ('sms', ))
        s.httpClient = HttpClient('GsmModem', skynet.conf.gsmModem['host'],
                                              skynet.conf.gsmModem['port'])
        s.TgHandlers = GsmModem.TgHandlers(s)


    def toAdmin(s, msg):
        s.tc.toAdmin("Gsm Modem: %s" % msg)


    def smsListener(s, source, type, data):
        phone = data['phone']
        msg = data['text']
        s.toAdmin("Поступило входящее SMS сообщение с номера %s:\n%s" % (phone, msg))


    def reqGet(s, op, args = {}):
        try:
            return s.httpClient.reqGet(op, args)
        except HttpClient.Error as e:
            raise GsmModemError(s.log, e) from e


    def reqPost(s, op, data, args = {}):
        try:
            return s.httpClient.reqPost(op, data, args)
        except HttpClient.Error as e:
            raise GsmModemError(s.log, e) from e


    def smsSend(s, phone, msg):
        s.reqPost('modem/sms_send',
                  json.dumps({'phone': phone,
                              'message': msg}))


    def balance(s):
        try:
            resp = s.reqGet('modem/balance')
            return resp['balance']
        except KeyError as e:
            raise GsmModemError(s.log, "field balance is absent in modem responce: %s" % resp)


    def stat(s):
        try:
            resp = s.reqGet('modem/stat')
            return resp['stat']
        except KeyError as e:
            raise GsmModemError(s.log, "field stat is absent in modem responce: %s" % resp)


    def textStat(s):
        text = "USB GSM модем:\n"
        try:
            text += "    Баланс счёта: %s руб\n" % s.balance()
        except AppError as e:
            text += "    Неудалось запросить баланс счёта: %s\n" % e
        try:
            st = s.stat()
            text += "    Уровень сигнала: %s%%\n" % st['SignalStrength']
            text += "    WAN IP адрес: %s\n" % st['WanIPAddress']
        except AppError as e:
            text += "    Неудалось запросить состояние модема: %s\n" % e
        return text


    class TgHandlers():
        def __init__(s, modem):
            s.modem = modem
            s.tc = modem.tc
            s.tc.registerHandler('gsmModem', s.balance, 'r', ('модем баланс',))
            s.tc.registerHandler('gsmModem', s.stat, 'r', ('модем статус',))
          #  s.tc.registerHandler('gsmModem', s.sendSms, 'w', ('отправь sms',))


        def balance(s, arg, replyFn):
            try:
                balance = s.modem.balance()
                replyFn("Баланс счёта: %s рублей" % balance)
            except GsmModemError as e:
                replyFn("Неудалось получить баланс счтёта модема: %s" % e)


        def stat(s, arg, replyFn):
            try:
                stat = s.modem.stat()
                replyFn("Статус модема:\n%s" % str(stat).replace(',', "\n"))
            except GsmModemError as e:
                replyFn("Неудалось получить статус модема: %s" % e)



