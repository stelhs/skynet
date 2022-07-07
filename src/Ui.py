import threading
from Exceptions import *
from HttpServer import *
from PeriodicNotifier import *
import os
import uuid
import time


class Ui():
    def __init__(s, skynet):
        s.skynet = skynet
        s.httpServer = skynet.httpServer


    def init(s):
        s.io = s.skynet.io
        s.users = s.skynet.users
        s.em = Ui.EventManager()
        s.httpHandlers = Ui.HttpHandlers(s)
        s.skynet.registerEventSubscriber('Ui', s.eventHandler,
                                         ('io', 'boiler', 'termosensors', 'power_sockets',
                                          'lighters', 'water_supply', 'gates', 'guard',
                                          'door_locks', 'ups'))



    def eventHandler(s, source, evType, data):
        s.em.send(source, evType, data)


    def setReqHandler(s, subsystem, permissionMode, method,
                        url, handler, requiredFields=[], retJson=True):
        def cb(args, conn):
            user = s.users.userByHttpConn(conn)
            if not user:
                raise HttpHandlerError("User not authorized", 'loginError')
            if not user.checkWebAccess(subsystem, permissionMode):
                raise HttpHandlerError("Permission denied")
            user.pinExtendAcceptance()
            handler(args, conn)
        s.httpServer.setReqHandler(method, url, cb, requiredFields, retJson)


    class EventManager():
        class Subsriber():
            def __init__(s, user):
                s.user = user
                s.lock = threading.Lock()
                s._events = []
                s.id = str(uuid.uuid4().hex)
                s.update()


            def update(s):
                with s.lock:
                    s.time = time.time()


            def isAlive(s):
                return (time.time() - s.time) < 5 * 60


            def pushEvent(s, event):
                if not s.user.checkWebAccess(event['source'], 'r'):
                    return
                with s.lock:
                    s._events.append(event)


            def pullEvents(s):
                with s.lock:
                    events = s._events
                    s._events = []
                    return events


        def __init__(s):
            s.lock = threading.Lock()
            s.awaitingTaskList = []
            s.subscribers = []


        def send(s, source, type, evData):
            s.removeOldSubscribers()

            ev = {'source': source, 'type': type, 'data': evData}
            for subscriber in s.subscribers:
                subscriber.pushEvent(ev)

            with s.lock:
                for task in s.awaitingTaskList:
                    task.sendMessage('event')


        def events(s, task, subsriberId):
            subscriber = s.subscriberById(subsriberId)
            if not subscriber:
                return None

            subscriber.update()
            events = subscriber.pullEvents()
            if len(events):
                return events

            with s.lock:
                s.awaitingTaskList.append(task)

            task.waitMessage(60)

            with s.lock:
                s.awaitingTaskList.remove(task)
            return subscriber.pullEvents()


        def subscribe(s, user):
            subscriber = Ui.EventManager.Subsriber(user)
            with s.lock:
                s.subscribers.append(subscriber)
            return subscriber


        def unSubscribe(s, id):
            print('unSubscribe')
            subscriber = s.subscriberById(id)
            if not subscriber:
                return
            s.subscribers.remove(subscriber)


        def subscriberById(s, id):
            with s.lock:
                for subscriber in s.subscribers:
                    if subscriber.id == id:
                        return subscriber
            return None


        def removeOldSubscribers(s):
            with s.lock:
                for subscriber in s.subscribers:
                    if not subscriber.isAlive():
                        s.subscribers.remove(subscriber)


    class HttpHandlers():
        def __init__(s, ui):
            s.ui = ui
            s.io = ui.io
            s.skynet = ui.skynet
            s.users = s.skynet.users
            s.httpServer = ui.httpServer
            s.httpServer.setReqHandler("GET", "/ui/get_teamplates", s.teamplates)
            s.httpServer.setReqHandler("GET", "/ui/get_events", s.events)
            s.httpServer.setReqHandler("GET", "/ui/subscribe", s.subscribe)
            s.httpServer.setReqHandler("GET", "/ui/configs", s.configs)
            s.httpServer.setReqHandler("GET", "/ui/logout", s.logout, ('subscriber_id',))
            s.httpServer.setReqHandler("GET", "/ui/pin_code", s.pinCodePermit, ('pin',))


        def teamplates(s, args, conn):
            tplDir = "%s/tpl" % s.httpServer.wwwDir()
            files = os.listdir(tplDir)
            list = {}
            for file in files:
                c = fileGetContent("%s/%s" % (tplDir, file))
                tplName = file.split('.')[0]
                list[tplName] = c

            return list


        def subscribe(s, args, conn):
            user = s.users.userByHttpConn(conn)
            if not user:
                try:
                    login = args['login']
                    password = args['password']
                    user = s.users.userByLogin(login)
                    if not user.checkPass(password):
                        raise HttpHandlerError("User or login is incorrect", 'loginError')
                    conn.setCookie('auth', user.secret())
                except KeyError:
                    raise HttpHandlerError("User or login is incorrect", 'loginError')
                except UserNotRegistredError:
                    raise HttpHandlerError("User or login is incorrect", 'loginError')

            subscriber = s.ui.em.subscribe(user)
            return {'subscriber_id': subscriber.id}


        def events(s, args, conn):
            if not 'subscriber_id' in args:
                raise HttpHandlerError("'subscriber_id' is absent", 'subscriberAbsent')
            subscriberId = args['subscriber_id']

            events = s.ui.em.events(conn.task(), subscriberId)
            if events == None:
                raise HttpHandlerError("'subscriberId' %s is not registred" % subscriberId, 'subscriberNotRegistred')
            return {'events': events}


        def configs(s, args, conn):
            return {"io": s.skynet.conf.io,
                    "guard": s.skynet.conf.guard,
                    "doorLocks": s.skynet.conf.doorLocks,
                    "powerSockets": s.skynet.conf.powerSockets,
                    "termosensors": s.skynet.conf.termosensors,
                    "lighters": s.skynet.conf.lighters,
                    "doorlocks": s.skynet.conf.doorLocks}


        def logout(s, args, conn):
            if not 'subscriber_id' in args:
                raise HttpHandlerError("'subscriber_id' is absent", 'subscriberAbsent')
            subscriberId = args['subscriber_id']

            user = s.users.userByHttpConn(conn)
            if not user:
                raise HttpHandlerError("User not logined")
            user.pinResetAcceptance()
            conn.removeCookie('auth')
            s.ui.em.unSubscribe(subscriberId)


        def pinCodePermit(s, args, conn):
            user = s.users.userByHttpConn(conn)
            if not user:
                raise HttpHandlerError("Can`t detect user")

            pin = args['pin']
            rc = user.pinAccept(pin)
            if not rc:
                raise HttpHandlerError("wrong pin code")




