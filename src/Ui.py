import threading
from HttpServer import *
from SubsystemBase import *
import os
import uuid
import time


class Ui(SubsystemBase):
    def __init__(s, httpServer, io):
        super().__init__("ui", {})
        s.em = Ui.EventManager()
        s.httpHandlers = Ui.HttpHandlers(s, httpServer, io)


    def listenedEvents(s):
        return ('io', 'mbio', 'boiler')


    def eventHandler(s, source, evType, data):
        s.em.send(source, evType, data)


    class EventManager():
        class Subsriber():
            def __init__(s):
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


        def subscribe(s):
            subscriber = Ui.EventManager.Subsriber()
            with s.lock:
                s.subscribers.append(subscriber)
            return subscriber


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
        def __init__(s, ui, httpServer, io):
            s.ui = ui
            s.io = io
            s.httpServer = httpServer
            s.httpServer.setReqHandler("GET", "/ui/get_teamplates", s.teamplatesHandler)
            s.httpServer.setReqHandler("GET", "/ui/get_events", s.eventsHandler)
            s.httpServer.setReqHandler("GET", "/ui/subscribe", s.subscribeHandler)


        def teamplatesHandler(s, args, body, attrs, conn):
            tplDir = "%s/tpl" % s.httpServer.wwwDir()
            files = os.listdir(tplDir)
            list = {}
            for file in files:
                c = fileGetContent("%s/%s" % (tplDir, file))
                tplName = file.split('.')[0]
                list[tplName] = c

            return list


        def subscribeHandler(s, args, body, attrs, conn):
            subscriber = s.ui.em.subscribe()
            return {'subscriber_id': subscriber.id}


        def eventsHandler(s, args, body, attrs, conn):
            if not 'subscriber_id' in args:
                raise HttpHandlerError("'subscriber_id' is absent", 'subscriberAbsent')

            subscriberId = args['subscriber_id']
            events = s.ui.em.events(conn.task(), subscriberId)
            if events == None:
                raise HttpHandlerError("'subscriberId' %s is not registred" % subscriberId, 'subscriberNotRegistred')
            return {'events': events}






