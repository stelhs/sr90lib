import threading
import time
from Syslog import *
from common import *
import traceback
from sr90Exceptions import *


class TaskStopException(Exception):
    pass


class Task():
    listTasks = []
    listTasksLock = threading.Lock()
    lastId = 0

    listAsyncFunctions = {}
    listAsyncLock = threading.Lock()

    taskErrorCb = None

    def __init__(s, name, fn=None, exitCb=None, autoremove=False):
        s._name = name
        s.fn = fn
        s.fnArgs = None
        s.exitCb = exitCb
        s.autoremove = autoremove
        s.log = Syslog("task_%s" % name)

        s._state = "stopped"
        s._tid = None
        s._removing = False
        s._msgQueue = []
        s._msgQueueLock = threading.Lock()
        s._apiLock = threading.Lock()


        if Task.taskByName(name):
            raise TaskAlreadyExistException(s.log, "Task with name '%s' is existed" % name)

        s.log.mute('debug')
        s.log.debug("created")
        s._ev = threading.Event()
        s._alive = False

        with Task.listTasksLock:
            Task.lastId += 1
            s._id = Task.lastId
            Task.listTasks.append(s)


    def iAmAlive(s):
        s._alive = True


    def checkForAlive(s):
        s._alive = False


    def isAlived(s):
        return s._alive


    def setFreezed(s):
        s.setState("freezed")


    def sendMessage(s, msg=""):
        s._msgQueue.append(msg)
        s._ev.set()


    def message(s):
        s._ev.clear()
        with s._msgQueueLock:
            if not len(s._msgQueue):
                return None

            msg = s._msgQueue[0]
            s._msgQueue.remove(msg)
            return msg


    def dropMessages(s):
        with s._msgQueueLock:
            s._msgQueue = []


    def waitMessage(s, timeoutSec = 0):
        sec = 0
        while 1:
            if timeoutSec and sec >= timeoutSec:
                break
            sec += 1
            s._ev.wait(1)
            if s.isRemoving():
                return s.message()
            msg = s.message()
            if msg:
                return msg
        return s.message()


    def start(s):
        with s._apiLock:
            if s.state() != "stopped":
                return
            s.log.debug("start")
            t = threading.Thread(target=s.thread, daemon=True, args=(s._name, ))
            t.start()
            s.setState("running")


    def setFn(s, cb, args=None):
        with s._apiLock:
            s.fn = cb
            s.fnArgs = args


    def thread(s, name):
        s._tid = threading.get_native_id()
        try:
            if s.fnArgs:
                s.fn(s.fnArgs)
            else:
                s.fn()
        except TaskStopException:
            s.log.debug("stopped")
        except Exception as e:
            with s._apiLock:
                trace = traceback.format_exc()
                s.log.err("Task %s Exception: %s" % (s.name(), trace))
                print("Task %s Exception: %s" % (s.name(), trace))
                if Task.taskErrorCb:
                    Task.taskErrorCb(s, trace)

        with s._apiLock:
            if s.exitCb:
                try:
                    s.exitCb()
                except TaskStopException:
                    pass

            s.setState("stopped")
            if s.isRemoving() or s.autoremove:
                with Task.listTasksLock:
                    Task.listTasks.remove(s)
                s.setState("removed")
                s.log.debug("removed by flag")


    def stop(s):
        with s._apiLock:
            if s.state() != "running":
                return
            s.log.debug("stopping")
            s.setState("stopping")


    def restart(s):
        s.stop()
        while 1:
            s.sleep(100)
            if s.state() == "stopped":
                break
        s.start()


    def pause(s):
        with s._apiLock:
            s.log.debug("paused")
            s.setState("paused")


    def resume(s):
        with s._apiLock:
            if s.state() != "paused":
                return
            s.log.debug("resumed")
            s.setState("running")


    def remove(s):
        with s._apiLock:
            if s.state() == "stopped":
                with Task.listTasksLock:
                    Task.listTasks.remove(s)
                s.setState("removed")
                s.log.debug("removed immediately")
                return

            s.log.debug("removing..")
            s.log.debug("stopping")
            s.setState("stopping")
            s._removing = True

        while 1:
            if s.state() == "removed":
                return
            s.sleep(100)


    def isRemoving(s):
        return s._removing


    def name(s):
        return s._name


    def id(s):
        return s._id


    def tid(s):
        return s._tid


    def setState(s, state):
        s._state = state
        s.log.debug("set state %s" % state)


    def state(s):
        return s._state


    @staticmethod
    def setErrorCb(cb):
        Task.taskErrorCb = cb


    @staticmethod
    def doObserveTasks():
        ot = Task.observeTask
        while 1:
            with Task.listTasksLock:
                for t in Task.listTasks:
                    if t.state() == "running":
                        t.checkForAlive()

            Task.sleep(10000)
            with Task.listTasksLock:
                for t in Task.listTasks:
                    if t.state() != "running":
                        continue
                    if not t.isAlived():
                        t.setFreezed()
                        if t.exitCb:
                            t.exitCb()
                        ot.log.info("task %d:%s is freezed" % (t.id(), t.name()))
                        ot.telegram.send("task %d:%s is freezed. Task stopped." % (t.id(), t.name()))


    @staticmethod
    def runObserveTasks():
        Task.observeTask = Task("observe", Task.doObserveTasks)
        Task.observeTask.start()


    @staticmethod
    def taskById(id):
        with Task.listTasksLock:
            for t in Task.listTasks:
                if t.id() == id:
                    return t
        return None


    @staticmethod
    def taskByTid(tid):
        with Task.listTasksLock:
            for t in Task.listTasks:
                if t.tid() == tid:
                    return t
        return None


    @staticmethod
    def taskByName(name):
        with Task.listTasksLock:
            for t in Task.listTasks:
                if t.name() == name:
                    return t
        return None


    @staticmethod
    def sleep(interval = 0):
        tid = Task.currTid()
        task = Task.taskByTid(tid)
        if not task:
#            print("sleep in not task %d" % interval)
            time.sleep(interval / 1000)
            return

        t = interval
        while (1):
            task.iAmAlive()
            if task.state() == "stopping":
                raise TaskStopException

            while(task.state() == "paused"):
                time.sleep(1/10)

            if t >= 100:
                time.sleep(1/10)
                t -= 100

            if t <= 0:
                break


    @staticmethod
    def asyncRunSingle(name, fn, exitCb = None):
        with Task.listAsyncLock:
            list = Task.listAsyncFunctions

        if name in list:
            with Task.listAsyncLock:
                task = Task.listAsyncFunctions[name]
            task.stop()
            task.remove()
            with Task.listAsyncLock:
                Task.listAsyncFunctions.pop(name)

        def do():
            fn()
            task.remove()
        task = Task("Async_%s" % name, do, exitCb)
        task.start()
        with Task.listAsyncLock:
            Task.listAsyncFunctions[name] = task
        return task


    @staticmethod
    def asyncRun(name, fn, exitCb = None):
        if not hasattr(Task.asyncRun, 'id'):
            Task.asyncRun.id = 1
        else:
            Task.asyncRun.id += 1

        def do():
            fn()
            task.remove()
        task = Task("Async_%s_%d" % (name, Task.asyncRun.id), do, exitCb)
        task.start()
        return task


    def __str__(s):
        str = "task %d:%s/%s:%s" % (s._id, s._name, s.state(), s.tid())
        if s._removing:
            str += ":removing"
        return str


    @staticmethod
    def setTimeout(name, interval, cb):
        def timeout():
            nonlocal task
            Task.sleep(interval)
            task.log.info("timeout expire")
            cb()
            task.remove()

        task = Task('timeout_task_%s' % name, timeout)
        task.start()
        return task


    @staticmethod
    def setPeriodic(name, interval, cb):
        def do():
            nonlocal task
            while 1:
                Task.sleep(interval)
                cb(task)

        task = Task('periodic_task_%s' % name, do)
        task.start()
        return task


    @staticmethod
    def currTid():
        return threading.get_native_id()


    @staticmethod
    def printList():
        with Task.listTasksLock:
            for tsk in Task.listTasks:
                print("%s" % tsk)



