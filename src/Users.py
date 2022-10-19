import time
from Exceptions import *
from HttpServer import *
from Syslog import *


class Users():
    def __init__(s, skynet):
       s.skynet = skynet
       s.conf = skynet.conf.users
       s._users = []
       s.log = Syslog('Users')

       for userConf in s.conf['users']:
            if 'enabled' in userConf and userConf['enabled']:
                user = User(s, userConf)
                s._users.append(user)


    def userByLogin(s, login):
        for user in s._users:
            if user.login() == login:
                return user
        raise UserNotRegistredError(s.log, 'User with login "%s" is not registred' % login)


    def userBySecret(s, secret):
        for user in s._users:
            if user.secret() == secret:
                return user
        raise UserNotRegistredError(s.log, 'User with secret "%s" is not registred' % secret)


    def userByIp(s, ip):
        for user in s._users:
            if user.matchWithIpAddr(ip):
                return user
        raise UserNotRegistredError(s.log, 'User associated with IP address %s is not registred' % ip)


    def userByHttpConn(s, conn):
        user = None
        try:
            user = s.userByIp(conn.remoteAddr())
        except HttpConnectionCookieError:
            pass
        except UserNotRegistredError:
            pass

        if not user:
            try:
                secret = conn.cookie('auth')
                user = s.skynet.users.userBySecret(secret)
            except HttpConnectionCookieError:
                pass
            except UserNotRegistredError:
                pass
        return user


    def userByTgId(s, tgUserId, tgUserName):
        for user in s._users:
            if user.tgChatId == tgUserId:
                return user
        raise UserNotRegistredError(s.log, 'User %s:%s is not registred' % (tgUserId, tgUserName))


    def users(s):
        return s._users




class User():
    def __init__(s, manager, userConf):
        s.manager = manager
        s._name = userConf['name']
        s._phones = userConf['phones'] if 'phones' in userConf else None
        s._tgId = userConf['telegramId'] if 'telegramId' in userConf else None

        s._uiLogin = None
        s._uiUserPass = None
        s._secret = None
        s.noAuthAddr = None
        s.webReadAccess = None
        s.webWriteAccess = None
        s.webWritePinAccess = None
        s.webWritePin = None
        s.pinAcceptedTime = 0

        s.tgWriteAccess = None
        s.tgChatId = None
        s.tgPrivateEnabled = False

        if 'web' in userConf:
            s.webReadAccess = userConf['web']['readAccess']
            s.webWriteAccess = userConf['web']['writeAccess']

            if 'writePinCode' in userConf['web']:
                s.webWritePin = userConf['web']['writePinCode']

            if 'writeAccessByPin' in userConf['web']:
                s.webWritePinAccess = userConf['web']['writeAccessByPin']

            if 'noAuthAddr' in userConf['web']:
                s.noAuthAddr = userConf['web']['noAuthAddr']
            else:
                s._uiLogin = userConf['web']['login']
                s._uiUserPass = userConf['web']['pass']
                s._secret = userConf['web']['secret']

        if 'telegram' in userConf:
            s.tgWriteAccess = userConf['telegram']['writeAccess']
            s.tgChatId = userConf['telegram']['chatId']
            if 'private' in userConf['telegram']:
                s.tgPrivateEnabled = userConf['telegram']['private']


    def name(s):
        return s._name


    def matchWithIpAddr(s, ip):
        if not s.noAuthAddr:
            return False
        if ip.find(s.noAuthAddr, 0) == 0:
            return True


    def login(s):
        return s._uiLogin


    def secret(s):
        return s._secret


    def checkPass(s, password):
        return password == s._uiUserPass


    def pinAccept(s, pin):
        if not s.webWritePin:
            return True
        now = int(time.time())
        if s.webWritePin == pin:
            s.pinAcceptedTime = now
            return True
        return False


    def pinAccepted(s):
        if not s.webWritePin:
            return True
        now = int(time.time())
        if now - s.pinAcceptedTime < 5 * 60:
            return True
        return False


    def pinResetAcceptance(s):
        s.pinAcceptedTime = 0


    def pinExtendAcceptance(s):
        if not s.pinAccepted():
            return
        now = int(time.time())
        s.pinAcceptedTime = now


    def checkWebAccess(s, subsystem, mode):
        def checkRead():
            permit = False
            if not s.webReadAccess:
                return False

            for word in s.webReadAccess:
                if word == 'all':
                    permit = True

                if word == subsystem:
                    permit = True

                if len(word) and word[0] == '-':
                    if word[1:] == subsystem:
                        permit = False
            return permit

        def checkWrite():
            permit = False
            for word in s.webWriteAccess:
                if word == 'all':
                    permit = True

                if word == subsystem:
                    permit = True
                if len(word) and word[0] == '-':
                    if word[1:] == subsystem:
                        permit = False
            return permit

        def ckeckWriteByPin():
            permit = False
            if not s.pinAccepted():
                return False

            if not s.webWritePinAccess:
                return False

            for word in s.webWritePinAccess:
                if word == 'all':
                    permit = True

                if word == subsystem:
                    permit = True

                if len(word) and word[0] == '-':
                    if word[1:] == subsystem:
                        permit = False
            return permit

        if mode == 'r':
            return checkRead()

        if mode == 'w':
            return checkRead() and (checkWrite() or ckeckWriteByPin())


    def checkTgWriteAccess(s, subsystem):
        if not s.tgWriteAccess:
            return False
        permit = False
        for word in s.tgWriteAccess:
            if word == 'all':
                permit = True

            if word == subsystem:
                permit = True

            if len(word) and word[0] == '-':
                if word[1:] == subsystem:
                    permit = False
        return permit


    def __repr__(s):
        return "User:%s" % s.name()


