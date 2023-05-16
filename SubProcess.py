import os, subprocess, signal, threading
from Syslog import *
from Task import *


class SubProcess():
    def __init__(s):
        s._procList = []
        s.lock = threading.Lock()
        s.log = Syslog('Subprocess')

#        def sigchldHandler(sig, frame):
 #           with s.lock:
  #              pid, _ = os.waitpid(-1, os.WNOHANG)
   #             sp = None
    #            for proc in s._procList:
     #               if proc._pid == pid:
      #                  proc._pid = None
       #                 sp = proc
        #                break

         #   if sp and sp._onStoppedCb:
          #      sp._onStoppedCb(sp)
#        signal.signal(signal.SIGCHLD, sigchldHandler)
        s.checkAliveTask = Task.setPeriodic('SubProcessCheckAlive',
                                            500, s.checkAlive)


    def processes(s):
        return s._procList


    def process(s, name):
        for proc in s._procList:
            if proc.name() == name:
                return proc
        raise SubProcessRegisterError(s.log, "process %s is not registred" % name)


    def register(s, name, cmd, onStoppedCb = None):
        for proc in s.processes():
            if proc.name() == name:
                raise SubProcessRegisterError(s.log,
                        "process with name '%s' already registred" % name)
        proc = SubProcess.Proc(s, name, cmd, onStoppedCb)
        s._procList.append(proc)
        return proc


    def unregister(s, name):
        proc = s.process(name)
        if proc.isStarted():
            proc.stop()
        s._procList.remove(proc)


    def __repr__(s):
        text = "SubProceses:\n"
        for proc in s._procList:
            text += "\t%s:%s%s\n" % (proc.name(),
                                    'started' if proc.isStarted() else 'stopped',
                                    (":%d" % proc.pid() if proc.pid() else ""))
        return text



    def checkAlive(s, task):
        for proc in s._procList:
            if not proc.isAlive():
                proc._pid = None
                proc.onStoppedCb(proc)



    def destroy(s):
        for proc in s.processes():
            if proc.isStarted():
                proc.stop()


    class Proc():
        def __init__(s, sp, name, cmd, onStoppedCb = None):
            s.sp = sp
            s._name = name
            s._cmd = [i for i in cmd.split(' ') if len(i)]
            s._pid = None
            s._proc = None
            s._onStoppedCb = onStoppedCb
            s._onStoppedCbTriggered = True
            s.log = Syslog('SubProcess:%s' % s.name())


        def name(s):
            return s._name


        def start(s):
            if s.isStarted():
                raise SubProcessCantStartError(s.log, "process %s already started" % s.name())
            with s.sp.lock:
                s._proc = subprocess.Popen(s._cmd, shell=False,
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE)
                s._pid = s._proc.pid
                s._onStoppedCbTriggered = False
            return s


        def stop(s):
            if not s.isStarted():
                raise SubProcessNotStartedError(s.log, 'process %s already stopped' % s.name())
            try:
                s._proc.kill()
            except ProcessLookupError as e:
                raise SubProcessNotStartedError(s.log, 'process %s already stopped: %s' % (
                                                 s.name(), e)) from e
            for cnt in range(10):
                Task.sleep(500)
                if not s.isStarted():
                    return
            raise SubProcessCantStopError(s.log, 'Can`t stop process %s. pid:%d' % (s.name(), s._pid))


        def isStarted(s):
            return s._pid != None


        def pid(s):
            return s._pid


        def stdout(s):
            return s._proc.stdout


        def stderr(s):
            return s._proc.stderr


        def isAlive(s):
            if not s._proc:
                return False
            return s._proc.poll() == None


        def onStoppedCb(s, proc):
            if s._onStoppedCb and not s._onStoppedCbTriggered:
                s._onStoppedCb(proc)
                s._onStoppedCbTriggered = True


        def __repr__(s):
            return "SubProcess:%s%s/%s" % (s.name(),
                    (":%s" % (s.pid() if s.pid() else "")),
                    ('started' if s.isStarted() else 'stopped'))




