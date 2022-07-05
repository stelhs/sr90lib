import threading, json
from sr90Exceptions import *
from Syslog import *
from common import *


class Storage():
    def __init__(s, fileName):
        s.storageDirectory = "storage/"
        s.log = Syslog('Storage_%s' % fileName)
        s.fileName = "%s%s" % (s.storageDirectory, fileName)
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
            s.log.info("storage file '%s' can't read: %s" % (s.fileName, e))
        except json.JSONDecodeError as e:
            s.log.info("storage file '%s' parse error: %s" % (s.fileName, e))
            s.data = {}


    def jsonData(s):
        return json.dumps(s.data, indent=4)


    def save(s):
        try:
            c = s.jsonData()
            with s._lock:
                filePutContent(s.fileName, c)
        except FileError as e:
            raise StorageSaveError(s.log,
                    "Can't write storage file '%s': %s" % (s.fileName, e)) from e


    def key(s, keyPath, default):
        with s._lock:
            if keyPath in s.keys:
                key = s.keys[keyPath]
                key.default = default
                return key

            key = Storage.Key(s, keyPath, default)
            s.keys[keyPath] = key
            return key


    def __repr__(s):
        return "storage:%s" % s.fileName


    def destroy(s):
        with s._lock:
            return


    class Key():
        def __init__(s, storage, keyPath, default):
            s.storage = storage
            items = keyPath.split('/')[1:]
            s.path = items[:-1]
            s.key = items[-1:][0]
            s.default = default
            s.val = default

            s.branch = s.storage.data
            for pathItem in s.path:
                if pathItem not in s.branch:
                    s.branch[pathItem] = {}
                s.branch = s.branch[pathItem]

            if s.key in s.branch:
                s.val = s.branch[s.key]


        def set(s, val):
            with s.storage._lock:
                if val == s.val:
                    return
                s.val = val
                s.branch[s.key] = val
            s.storage.save()


        def __repr__(s):
            return str(s.val)


