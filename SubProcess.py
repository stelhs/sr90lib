import os, subprocess, signal, threading
from Syslog import *
from Task import *


class SubProcess():
    def __init__(s):
        s._procList = []
        s.log = Syslog('Subprocess')
        s.restartTask = Task.setPeriodic('restarter_subprocesses',
                                         1000, s.checkForRestart)


    def processes(s):
        return s._procList


    def process(s, name):
        for proc in s._procList:
            if proc.name() == name:
                return proc
        raise SubProcessRegisterError(s.log, "process %s is not registred" % name)


    def register(s, name, cmd, autoRestart=False, onStoppedCb=None):
        for proc in s.processes():
            if proc.name() == name:
                raise SubProcessRegisterError(s.log,
                        "process with name '%s' already registred" % name)
        proc = SubProcess.Proc(s, name, cmd, autoRestart, onStoppedCb)
        s._procList.append(proc)
        return proc


    def unregister(s, name):
        proc = s.process(name)
        if proc.isStarted():
            proc.stop()
        s._procList.remove(proc)


    def checkForRestart(s, t):
        for proc in s.processes():
            proc.checkForRestart()


    def __repr__(s):
        text = "SubProceses:\n"
        for proc in s._procList:
            text += "\t%s:%s%s\n" % (proc.name(),
                                    'started' if proc.isStarted() else 'stopped',
                                    (":%d" % proc.pid() if proc.pid() else ""))
        return text


    def destroy(s):
        for proc in s.processes():
            if proc.isStarted():
                proc._onStoppedCb = None
                proc.stop()


    class Proc():
        def __init__(s, sp, name, cmdFn, autoRestart=False, onStoppedCb=None):
            s.sp = sp
            s._name = name
            s._cmdFn = cmdFn
            s._pid = None
            s._started = False
            s._proc = None
            s._startStopLock = threading.Lock()
            s._onStoppedCb = onStoppedCb
            s.log = Syslog('SubProcess:%s' % s.name())
            s.observerTask = Task('subprocess_%s' % s.name(), s.observerDo)
            s._autoRestartFlag = autoRestart
            s._stdout = ""


        def name(s):
            return s._name


        def start(s):
            with s._startStopLock:
                if s.isStarted():
                    raise SubProcessCantStartError(s.log, "process %s already started %s" % (
                                                   s.name(), s.pid()))
                s.startProc()
                s._started = True


        def stop(s):
            with s._startStopLock:
                if not s.isStarted():
                    raise SubProcessNotStartedError(s.log, 'process %s already stopped' % (
                                                    s.name()))
                s._started = False
                s.stopProc()


        def restart(s):
            with s._startStopLock:
                if not s.isStarted():
                    raise SubProcessCantStartError(s.log, "process %s not started" % (
                                                   s.name()))
                s.stopProc()
                s.startProc()



        def startProc(s):
            if s.isRun():
                return
            try:
                s._proc = subprocess.Popen(s._cmdFn(), shell=False,
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.STDOUT,
                                           text=True,
                                           preexec_fn=os.setsid)
                s._pid = s._proc.pid
                s.observerTask.start()
            except IOError as e:
                raise SubProcessCantStartError(s.log, "can't start process: %s" % e)
            return s


        def stopProc(s):
            try:
                s._proc.kill()
            except ProcessLookupError as e:
                raise SubProcessNotStartedError(s.log, 'process %s already stopped: %s' % (
                                                 s.name(), e)) from e
            for cnt in range(10):
                Task.sleep(500)
                if not s.isRun():
                    return
            raise SubProcessCantStopError(s.log, 'Can`t stop process %s. pid:%s' % (s.name(), s._pid))


        def pid(s):
            return s._pid


        def stdout(s):
            return s._stdout


        def isStarted(s):
            return s._started


        def isRun(s):
            return s._pid != None


        def observerDo(s):
            out = s._proc.stdout
            while 1:
                t = out.readline()
                if len(t) == 0:
                    break
                s._stdout += t
                if len(s._stdout) > 1024 * 100:
                    s._stdout = s._stdout[-1024 * 100:]

            cnt = 0
            while s._proc.poll() == None:
                Task.sleep(100)
                cnt += 1
                if cnt > 10:
                    print("gavno")
                    break

            if s._onStoppedCb:
                def fin():
                    s._started = False
                s._onStoppedCb(s, s._proc.poll(), fin)
            s._pid = None


        def checkForRestart(s):
            if not s._autoRestartFlag:
                return

            if not s.isStarted():
                return

            if not s.isRun():
                s.startProc()


        def __repr__(s):
            return "SubProcess:%s%s/%s/%s" % (s.name(),
                    (":%s" % (s.pid() if s.pid() else "")),
                    ('started' if s.isStarted() else 'stopped'),
                    ('run' if s.isRun() else 'not_run'))




