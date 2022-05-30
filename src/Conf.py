from Exceptions import *
from common import *
from Skynet import *
from Syslog import *
import os
import json


class Conf():
    def __init__(s):
        s.log = Syslog('Conf')
        s.confDirectory = "configs/"
        try:
            s.confDirectory = fileGetContent(".configs_dir")
        except:
            pass

        s.addConfig('db', 'database.conf')
        s.addConfig('io', 'io.conf')
        s.addConfig('boiler', 'boiler.conf')
        s.addConfig('skynet', 'skynet.conf')
        s.addConfig('telegram', 'telegram.conf')
        s.addConfig('termosensors', 'termosensors.conf')


    def stripComments(s, text):
        stripped = ""
        lines = text.split("\n")
        for line in lines:
            pos = line.find('//')
            if pos != -1:
                line = line[:pos]
            stripped += "%s\n" % line
        return stripped


    def loadConfig(s, fileName):
        try:
            c = fileGetContent("%s/%s" % (s.confDirectory, fileName))
        except Exception as e:
            msg = "Can't loading config file %s: %s" % (fileName, e)
            s.log.err(msg)
            raise ConfigError(s.log, msg) from e

        c = s.stripComments(c)
        try:
            conf = json.loads(c)
            return conf
        except json.JSONDecodeError as e:
            msg = "config file %s parse error: %s" % (fileName, e)
            s.log.err(msg)
            raise ConfigError(s.log, msg) from e


    def addConfig(s, var, fileName):
        conf = s.loadConfig(fileName)
        exec('s.%s = %s' % (var, conf))


