import threading
from Task import *


class PeriodicNotifier():
    def __init__(s):
        s._updaters = []
        s.task = Task('periodic_notifier', s.do)
        s.task.start()


    def do(s):
        while 1:
            Task.sleep(100)
            for upd in s._updaters:
                upd.incTime(100)


    def register(s, name, fn, interval):
        upd = PeriodicNotifier.Updater(name, fn, interval)
        s._updaters.append(upd)
        return upd


    def updaters(s):
        return s._updaters


    class Updater():
        def __init__(s, name, fn, interval):
            s._name = name
            s._lock = threading.Lock()
            s.update = fn
            s.interval = interval
            s.cnt = 0


        def name(s):
            return s._name


        def call(s):
            with s._lock:
                s.cnt = 0
                s.update()


        def incTime(s, interval):
            with s._lock:
                s.cnt += interval
                cnt = s.cnt
            if cnt >= s.interval:
                s.call()

        def __repr__(s):
            return "PeriodicNotifier.Updater:%s" % s.name()
