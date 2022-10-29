from TelegramClient import *
from Users import *


class TelegramClientSkynet(TelegramClient):
    def __init__(s, skynet):
        super().__init__(skynet.conf.telegram, s.receiver)
        s.skynet = skynet
        s.db = skynet.db

        s.mutePublic = skynet.conf.skynet['mute_public']
        s.handlers = []

    def toAdmin(s, msg):
        s.sendToChat('stelhs', "Skynet: %s" % msg)


    def toSkynet(s, msg):
        if s.mutePublic:
            return s.toAdmin('toSkynet: %s' % msg)
        s.sendToChat('skynet', "Skynet: %s" % msg)


    def toAlarm(s, msg):
        if s.mutePublic:
            return s.toAdmin('toAlarm: %s' % msg)
        s.sendToChat('alarm', "Skynet: %s" % msg)


    def receiver(s, text, msgId, date, fromName, fromId, chatId, chatType, chatName, updateId):
        def reply(msg):
            s.send(chatId, msg, msgId)

        try:
            s.db.insert('telegram_msg',
                        {'update_id': updateId,
                         'msg_id': msgId,
                         'date': date,
                         'from_name': fromName,
                         'from_id': fromId,
                         'chat_id': chatId,
                         'chat_name': chatName,
                         'chat_type': chatType,
                         'text': text})
        except DatabaseConnectorError as e:
            pass

        words = text.split()
        if not len(words):
            return

        keyword = words[0].lower()
        if keyword != 'skynet' and keyword != 'скайнет':
            return

        try:
            user = s.skynet.users.userByTgId(fromId, fromName)
        except UserNotRegistredError:
            return reply("У вас нет прав доступа")

        if len(words) == 1:
            return s.sendHelp(chatId, msgId)

        handlerText = " ".join(words[1:])

        requestProcessed = False
        for h in s.handlers:
            if not h.match(handlerText):
                continue

            requestProcessed = True
            try:
                if not user.checkTgWriteAccess(h.sysName()):
                    reply("У вас нет прав доступа для выполнения этой операции")
                    continue

                if h.accessMode() == 'r':
                    if chatName != 'SKYNET' and not user.tgPrivateEnabled:
                        reply("У вас нет прав доступа для выполнения этой операции")
                        continue

                h.call(handlerText, reply)
            except AppError as e:
                reply("Handler %s return error: %s" % (h.name(), e))

        if not requestProcessed:
            reply("Такое не понимаю")


    def sendHelp(s, chatId, replyMsgId):
        msg = "Слушаю вас внимательно!\n" \
              "Доступные команды:\n\n"

        systems = []
        for h in s.handlers:
            if h.sysName() not in systems:
                systems.append(h.sysName())

        for sysName in systems:
            handlers = s.handlersBySysName(sysName)

            for h in handlers:
                msg += "\t\t\tskynet %s\n" % h.cmdList[0]
            msg += "\n"
        s.send(chatId, msg, replyMsgId)


    def handlersBySysName(s, sysName):
        return [h for h in s.handlers if h.sysName() == sysName]


    def registerHandler(s, sysName, cb, accessMode, cmdList):
        sb = TelegramClientSkynet.Handler(sysName, cmdList, cb, accessMode)
        s.handlers.append(sb)


    class Handler():
        def __init__(s, sysName, cmdList, cb, accessMode):
            s._name = sysName
            s.cmdList = cmdList
            s.cb = cb
            s._accessMode = accessMode


        def sysName(s):
            return s._name


        def accessMode(s):
            return s._accessMode


        def match(s, text):
            for cmd in s.cmdList:
                if text.find(cmd) == 0:
                    return True
            return False


        def call(s, text, replyFn):
            for cmd in s.cmdList:
                if text.find(cmd) == 0:
                    break
            arg = text.replace(cmd, '')
            return s.cb(arg, replyFn)


        def __repr__(s):
            return "TelegramClientSkynet.Handler:%s:%s" % (s.sysName(), s.cmdList[0])





