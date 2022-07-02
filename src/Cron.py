from Exceptions import *
from Task import *


class Cron():
    def __init__(s):
        s.task = Task.setPeriodic('cron', 1000, s.do)
        s.workers = []


    def do(s):
        for wrk in s.workers:
            wrk.incTime()


    def registerEveryMin(s, name, fn):
        wrk = Cron.Worker(name, 60, fn)
        s.workers.append(wrk)


    class Worker():
        def __init__(s, name, intervalSec, fn):
            s.name = name
            s.interval = intervalSec
            s.fn = fn
            s.cnt = 0


        def incTime(s):
            s.cnt += 1
            if s.cnt >= s.interval:
                s.cnt = 0
                s.fn()


        def __repr__(s):
            return "Cron.Worker:%s" % s.name
