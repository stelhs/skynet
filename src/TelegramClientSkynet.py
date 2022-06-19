from TelegramClient import *


class TelegramClientSkynet(TelegramClient):
    def __init__(s, skynet, recever=None):
        super().__init__(skynet.conf.telegram, recever)
        s.mutePublic = skynet.conf.skynet['mute_public']

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



