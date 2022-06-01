from common import *
from sr90Exceptions import *
from Syslog import *
import os
import json

class ConfParser():
    def __init__(s):
        s.log = Syslog('Conf')
        s.confDirectory = "configs/"
        try:
            s.confDirectory = fileGetContent(".configs_dir")
        except:
            pass


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


