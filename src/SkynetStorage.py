from Storage import *


class SkynetStorage(Storage):
    def __init__(s, skynet, fileName):
        s.skynet = skynet
        storageDir = skynet.conf.skynet['storageDir']
        super().__init__(fileName, storageDir)
