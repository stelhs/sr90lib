import re, os
from Task import *
from common import *
from Syslog import *
from AveragerQueue import *


class TermoSensorDs18b20():
    class Error(Exception):
        pass

    class TemperatureError(Error):
        pass

    class NoDataError(Error):
        pass

    def __init__(s, addr, observerCb = None, minT = None, maxT = None):
        s._addr = addr
        s._minT = float(minT)
        s._maxT = float(maxT)
        s.error = None
        s.observerCb = observerCb
        s.log = Syslog("termo_sensor_%s" % addr)
        s._fake = None
        s._t = None
        s._updatedTime = None
        s.prev_t = None
        s.queue = AveragerQueue(10)

        s.task = Task("termo_sensor_%s" % addr, s.do)
        s.task.start()

        if os.path.exists('FAKE'):
            s._fake = True

        if s._fake:
            s._fakeFileName = 'FAKE/%s' % addr
            if not os.path.exists(s._fakeFileName):
                filePutContent(s._fakeFileName, "18.0")
            return


    def addr(s):
        return s._addr


    def t(s):
        if s._fake:
            return float(fileGetContent(s._fakeFileName))

        if s.error:
            raise TermoSensorDs18b20.TemperatureError(s.error)

        if (not s._updatedTime) or (s.timeNow() - s._updatedTime > 5) or s._t == None:
            raise TermoSensorDs18b20.NoDataError('%s: No temperature data' % s._addr)

        return s._t


    def timeNow(s):
        return int(time.time())


    def do(s):
        while True:
            Task.sleep(1000)
            try:
                with open("/sys/bus/w1/devices/%s/w1_slave" % s._addr, "r") as f:
                    f.seek(0)
                    content = f.read().strip()
            except OSError as e:
                s.error = 'Can`t read device file: %s' % e
                Task.sleep(1000)
                continue

            try:
                t = float(re.findall("t=([\d-]+)", content)[0]) / 1000.0
                s.error = ""
            except IndexError:
                s.error = "parse error: %s" % content
                continue
            except ValueError:
                s.error = "parse float error: %s" % content
                continue

            s.queue.push(t)
            s._t = s.queue.round()
            s._updatedTime = s.timeNow()

            if s._maxT and t > s._maxT:
                s.error = "sensor %s failure %.2f > %.2f" % (s._addr, t, s._maxT)
            elif s._minT and t < s._minT:
                s.error = "sensor %s failure %.2f < %.2f" % (s._addr, t, s._minT)
            else:
                s.error = None

            t = None
            if s.observerCb and s._t != s.prev_t:
                t = s._t
            s.prev_t = s._t

            if s.observerCb and t != None:
                s.observerCb(s, t, s.error)




    def destroy(s):
        if s.task:
            s.task.remove()


    def __repr__(s):
        return "TermoSensorDs18b20:%s" % s._addr


    def __str__(s):
        return "%s:%.1f" % (s._addr, s.t())




