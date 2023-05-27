from datetime import date
from Exceptions import *
from HttpServer import *
from Skynet import *
from HttpClient import *


class Dvr():
    def __init__(s, skynet):
        s.log = Syslog('Dvr')
        s.skynet = skynet
        s.tc = skynet.tc
        s.conf = skynet.conf.dvr
        s.httpServer = skynet.httpServer
        s.db = skynet.db
        s.TgHandlers = Dvr.TgHandlers(s)

        s.httpClient = HttpClient('dvr', s.conf['host'], s.conf['port'])


    def send(s, op, args = {}):
        try:
            return s.httpClient.reqGet(op, args)
        except HttpClient.Error as e:
            raise DvrError(s.log, e) from e


    def start(s, cName):
        s.send('dvr/start', {'cname': cName})


    def stop(s, cName):
        s.send('dvr/stop', {'cname': cName})


    def stat(s):
        return s.send('dvr/stat')


    def textStat(s):
        try:
            st = s.stat()
        except DvrError as e:
            return "Ошибка при запросе статуса DVR: %s\n" % e

        text = "DVR:\n"
        text += "    Размер видео-архива: %.2fGb\n" % (st['vrTotalSize'] / (1024*1024*1024))
        text += "    Длительность видео-архива: %s\n" % timeDurationStr(st['vrTotalDuration'])
        text += "    Видеокамеры:\n"
        cnt = 1
        for inf in st['camcorders']:
            text += "        %d) %s: %s, %s, размер:%.2fGb, %s\n" % (
                     cnt,
                     inf['desc'],
                     'запущена' if inf['isRecordStarted'] else 'не запущена',
                     'пишется' if inf['isRecording'] else 'не пишется',
                     inf['vrDataSize'] / (1024*1024*1024),
                     timeDurationStr(inf['vrDuration']))
            cnt += 1
        return text


    def __repr__(s):
        return s.textStat()




    class TgHandlers():
        def __init__(s, dvr):
            s.dvr = dvr
            s.tc = dvr.tc
            s.tc.registerHandler('dvr', s.stat, 'w', ('dvr статус', 'dvr status'))


        def stat(s, arg, replyFn):
            replyFn(s.dvr.textStat())




