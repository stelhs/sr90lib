import threading, json
from sr90Exceptions import *
from Syslog import *
from common import *


class Settings():
    def __init__(s, fileName):
        s.settingsDirectory = "settings/"
        s.log = Syslog('Settings_%s' % fileName)
        s.fileName = "%s%s" % (s.settingsDirectory, fileName)
        s.data = {}
        s.keys = {}
        s._lock = threading.Lock()
        s.load()


    def load(s):
        try:
            c = fileGetContent(s.fileName)
            with s._lock:
                s.data = json.loads(str(c))
        except FileError as e:
            s.log.info("settings file '%s' can't read: %s" % (s.fileName, e))
        except json.JSONDecodeError as e:
            s.log.info("settings file '%s' parse error: %s" % (s.fileName, e))
            s.data = {}


    def save(s):
        try:
            c = json.dumps(s.data, indent=4)
            with s._lock:
                filePutContent(s.fileName, c)
        except FileError as e:
            raise SettingsSaveError(s.log,
                    "Can't write settings file '%s': %s" % (s.fileName, e)) from e


    def key(s, keyPath, default, keyType='array'):
        with s._lock:
            if keyPath in s.keys:
                key = s.keys[keyPath]
                key.keyType = keyType
                key.default = default
                return key

            key = Settings.Key(s, keyPath, keyType, default)
            s.keys[keyPath] = key
            return key


    def __repr__(s):
        return "settings:%s" % s.fileName



    class Key():
        def __init__(s, settings, keyPath, default, keyType):
            s.settings = settings
            items = keyPath.split('/')[1:]
            s.path = items[:-1]
            s.key = items[-1:][0]
            s.keyType = keyType
            s.default = default
            s.val = default

            s.branch = s.settings.data
            for pathItem in s.path:
                if pathItem not in s.branch:
                    s.branch[pathItem] = {}
                s.branch = s.branch[pathItem]

            if s.key in s.branch:
                s.val = s.branch[s.key]


        def set(s, val):
            with s.settings._lock:
                s.val = val
                s.branch[s.key] = str(val)
            s.settings.save()


        def __repr__(s):
            if s.keyType == 'str':
                return str(s.val)
            if s.keyType == 'int':
                return int(s.val)
            if s.keyType == 'float':
                return float(s.val)
            if s.keyType == 'array':
                return s.val





