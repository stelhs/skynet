import threading
import mysql.connector
from Syslog import *

class MySQL():

    def __init__(s, conf):
        s._lock = threading.Lock()
        s.log = Syslog('Mysql')
        s.conf = conf
        s.conn = None


    def isClosed(s):
        with s._lock:
            if s.conn:
                return s.conn.is_closed()
            return True


    def connect(s):
        if not s.isClosed():
            return

        with s._lock:
            s.conn = mysql.connector.connect(host = s.conf['host'],
                                             user = s.conf['user'],
                                             password = s.conf['pass'],
                                             database = s.conf['database'])

            with s.conn.cursor() as cursor:
                cursor.execute('set character set utf8')
                cursor.execute('set names utf8')
                cursor.execute('SET AUTOCOMMIT=1')
            s.log.info('Connection was established')


    def close(s):
        with s._lock:
            if s.conn:
                s.conn.close()
            s.conn = None
        s.log.info('Connection closed')


    def query(s, query):
        with s._lock:
            if not s.conn:
                raise mysql.connector.errors.OperationalError('MySQL Connection not available')

            with s.conn.cursor(dictionary = True) as cursor:
                cursor.execute(query)
                data = cursor.fetchall()
                if not len(data):
                    return []
                return data[0]


    def queryList(s, query):
        with s._lock:
            if not s.conn:
                raise mysql.connector.errors.OperationalError('MySQL Connection not available')

            with s.conn.cursor(dictionary = True) as cursor:
                cursor.execute(query)
                data = cursor.fetchall()
                return data


    def insert(s, tableName, dataWithComma, dataWithOutComma = []):
        with s._lock:
            if not s.conn:
                raise mysql.connector.errors.OperationalError('MySQL Connection not available')

            query = "insert into %s SET" % tableName
            sep = ''
            for field, val in dataWithComma.items():
                if field == 'id':
                    continue
                query += '%s`%s`="%s"' % (sep, field, val)
                sep = ','

            if len(dataWithOutComma):
                for field, val in dataWithOutComma.items():
                    if field == 'id':
                        continue
                    query += '%s`%s`=%s' % (sep, field, val)
                    sep = ','

            with s.conn.cursor(dictionary = True) as cursor:
                cursor.execute(query)
                return cursor.lastrowid


    def update(s, tableName, id, dataWithComma, dataWithOutComma = []):
        with s._lock:
            if not s.conn:
                raise mysql.connector.errors.OperationalError('MySQL Connection not available')

            query = "update %s set " % tableName
            sep = ''
            for field, val in dataWithComma.items():
                if field == 'id':
                    continue
                query += '%s`%s`="%s"' % (sep, field, val)
                sep = ','

            if len(dataWithOutComma):
                for field, val in dataWithOutComma.items():
                    if field == 'id':
                        continue
                    query += '%s`%s`=%s' % (sep, field, val)
                    sep = ','

            query += " where id = %d" % id;
            with s.conn.cursor(dictionary = True) as cursor:
                cursor.execute(query)

