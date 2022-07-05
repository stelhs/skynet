import threading
from Exceptions import *
from Syslog import *
from Task import *
from MySQL import *


class DatabaseConnector():
    def __init__(s, skynet, conf):
        s.skynet = skynet
        s.conf = conf
        s.tc = skynet.tc
        s.log = Syslog('DatabaseConnector')
        s.mysql = MySQL(conf)
        s.attempts = 0
        s.task = Task('DatabaseConnector', s.reconnector)
        s.task.start()
        s._lock = threading.Lock()


    def toAdmin(s, msg):
        s.tc.toAdmin("DatabaseConnector: %s" % msg)


    def reconnector(s):
        while 1:
            if s.attempts > 30:
                s.toAdmin('Can`t connect to MySQL server')
                s.attempts = 0

            if not s.mysql.isClosed():
                s.mysql.close()

            try:
                s.mysql.connect()
            except mysql.connector.errors.DatabaseError:
                s.attempts += 1
                Task.sleep(1000)
                continue

            s.attempts = 0
            s.task.dropMessages()
            s.task.waitMessage()


    def waitForConnect(s):
        s.task.sendMessage('doConnect')
        while 1:
            Task.sleep(500)
            if not s.mysql.isClosed():
                break


    def query(s, query):
        if s.mysql.isClosed():
            s.waitForConnect()

        while 1:
            try:
                with s._lock:
                    return s.mysql.query(query)
            except mysql.connector.errors.OperationalError as e:
                s.log.info('Cant request query(): SQL query: "%s". Error: %s' % (query, e))
                s.waitForConnect()
            except mysql.connector.errors.Error as e:
                raise DatabaseConnectorError(s.log, "query() '%s' error: %s" % (query, e)) from e


    def queryList(s, query):
        if s.mysql.isClosed():
            s.waitForConnect()

        while 1:
            try:
                with s._lock:
                    return s.mysql.queryList(query)
            except mysql.connector.errors.OperationalError as e:
                s.log.info('Cant request queryList(): SQL query: "%s". Error: %s' % (query, e))
                s.waitForConnect()
            except mysql.connector.errors.Error as e:
                raise DatabaseConnectorError(s.log, "queryList() '%s' error: %s" % (query, e)) from e


    def insert(s, tableName, dataWithComma=[], dataWithOutComma=[]):
        if s.mysql.isClosed():
            s.waitForConnect()

        while 1:
            try:
                with s._lock:
                    return s.mysql.insert(tableName, dataWithComma, dataWithOutComma)
            except mysql.connector.errors.OperationalError as e:
                s.log.info('Cant insert to table "%s": Error: %s' % (tableName, e))
                s.waitForConnect()
            except mysql.connector.errors.Error as e:
                raise DatabaseConnectorError(s.log,
                        "insert() in table %s error: %s" % (tableName, e)) from e


    def update(s, tableName, id, dataWithComma=[], dataWithOutComma=[]):
        if s.mysql.isClosed():
            s.waitForConnect()

        while 1:
            try:
                with s._lock:
                    return s.mysql.update(tableName, id, dataWithComma, dataWithOutComma)
            except mysql.connector.errors.OperationalError as e:
                s.log.info('Cant update table "%s": SQL query: "%s". Error: %s' % (tableName, query, e))
                s.waitForConnect()
            except mysql.connector.errors.Error as e:
                raise DatabaseConnectorError(s.log, "insert() '%s' error: %s" % (query, e)) from e
            except mysql.connector.errors.Error as e:
                raise DatabaseConnectorError(s.log,
                        "update() table %s, id:%d error: %s" % (tableName, id, e)) from e


    def destroy(s):
        print("destroy DatabaseConnector")
        with s._lock:
            s.mysql.close()



