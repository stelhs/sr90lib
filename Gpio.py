import os, select
from Task import *
from common import *
from Syslog import *
from sr90Exceptions import *



class Gpio():
    poll = select.poll()
    task = Task('gpio_events')
    log = Syslog("gpios")

    _usedGpio = []
    def __init__(s, num, name="", mode='not_configured'):
        s._num = num
        s._name = name
        s._fake = False
        s._timeoutTask = None
        s.eventCb = None
        s.prevVal = None
        s._of = None

        s._lock = threading.Lock()
        s._gpioLock = threading.Lock()
        s.log = Syslog("gpio%d" % (s._num))
        s.log.mute('debug')

        try:
            if Gpio.gpioByNum(num):
                raise GpioNumberIsBusyError(s.log,
                    "Can't register new GPIO %d: gpio already in used" % num)
        except:
            pass

        s._usedGpio.append(s)
        if os.path.exists('FAKE'):
            s._fake = True

        s.setMode(mode)


    def setMode(s, mode):
        s._mode = mode
        if s._fake:
            s.initFake()
        else:
            s.initReal()


    def mode(s):
        return s._mode


    def num(s):
        return s._num;


    def name(s):
        return s._name


    def fd(s):
        if s._of:
            return s._of.fileno();
        return None


    def initReal(s):
        if s._of:
            close(s._of)

        if s._mode == 'not_configured':
            if os.path.exists("/sys/class/gpio/gpio%d" % s._num):
                filePutContent("/sys/class/gpio/gpio%d/direction" % s._num, 'in')
                filePutContent("/sys/class/gpio/unexport", "%d" % s._num)
            return

        if not os.path.exists("/sys/class/gpio/gpio%d" % s._num):
            filePutContent("/sys/class/gpio/export", "%d" % s._num)

        mode = fileGetContent("/sys/class/gpio/gpio%d/direction" % s._num).strip()
        if mode != s._mode:
            filePutContent("/sys/class/gpio/gpio%d/direction" % s._num, s._mode)

        filePutContent("/sys/class/gpio/gpio%d/edge" % s._num, "both")
        s._of = open("/sys/class/gpio/gpio%d/value" % s._num, "r+")


    def initFake(s):
        s._fileName = "FAKE/GPIO%d_%s" % (s._num, s._mode)

        if not os.path.exists(s._fileName):
            if s._mode == 'in':
                filePutContent(s._fileName, "1")
            else:
                filePutContent(s._fileName, "0")

        s._of = None


    def setValueReal(s, val):
        with s._gpioLock:
            s._of.seek(0)
            s._of.write("%d" % val)
            s._of.flush()


    def setValueFake(s, val):
        filePutContent(s._fileName, "%d" % val)


    def setValue(s, val):
        if s._mode == 'not_configured':
            raise GpioIncorrectStateError(s.log,
                    "Can't setValue() GPIO:%d does not configured" % s._num)

        if s._mode == 'in':
            raise GpioIncorrectStateError(s.log,
                    "Can't setValue() GPIO:%d configured as input" % s._num)

        with s._lock:
            if s._timeoutTask:
                s.log.debug('cancel setValueTimeout')
                s._timeoutTask.remove()
                s._timeoutTask = None

        if s._fake:
            return s.setValueFake(val)
        return s.setValueReal(val)


    def valueFake(s):
        c = fileGetContent(s._fileName)
        return int(c.strip())


    def valueReal(s):
        with s._gpioLock:
            s._of.seek(0)
            c = s._of.read()
        return int(c.strip())


    def value(s):
        if s._mode == 'not_configured':
            raise GpioIncorrectStateError(s.log,
                    "Can't get value(), GPIO:%d does not configured" % s._num)

        if s._fake:
            val = s.valueFake()
        else:
            val = s.valueReal()
        s.prevVal = val
        return val


    def setValueTimeout(s, val, interval):
        if s._mode == 'not_configured':
            raise GpioIncorrectStateError(s.log,
                    "Can't setValueTimeou(), GPIO:%d does not configured" % s._num)

        with s._lock:
            if s._timeoutTask:
                s._timeoutTask.remove()
                s._timeoutTask = None

        def timeout():
            if s._fake:
                s.setValueFake(val)
            else:
                s.setValueReal(val)

            with s._lock:
                s._timeoutTask = None
            s.log.debug("set to value '%d' by timeout: %d mS" % (val, interval))

        task = Task.setTimeout('gpio_%s_%dmS' % (s._num, interval), interval, timeout)
        with s._lock:
            s._timeoutTask = task


    def setEventCb(s, cb):
        if s._fake:
            return

        if not s._of:
            raise GpioNotConfiguredError(s.log,
                    "Can't setEventCb(): GPIO:%d file does not opened" % s._num)

        s.poll.register(s._of.fileno(), select.POLLPRI)
        s.eventCb = cb


    def unsetEvent(s):
        if s._fake:
            return

        if not s._of:
            return

        if not s.eventCb:
            return

        s.poll.usregister(s._of.fileno())
        s.eventCb = None


    def reset(s):
        with s._lock:
            task = s._timeoutTask
            if task:
                task.stop()
        s.unsetEvent()
        s.setMode('not_configured')

    def __str__(s):
        return "GPIO:%d_%s" % (s._num, s._mode)


    @staticmethod
    def gpioByNum(num):
        for gpio in Gpio._usedGpio:
            if gpio.num() == num:
                return gpio
        raise GpioNotRegistredError(Gpio.log,
                "gpioByNum() failed: Gpio with number '%s' is not registred" % num)


    @staticmethod
    def gpioByFd(fd):
        for gpio in Gpio._usedGpio:
            if gpio.fd() == fd:
                return gpio
        raise GpioNotRegistredError(Gpio.log,
                "gpioByFd() failed: Gpio with fd '%s' is not registred" % fd)


    @staticmethod
    def printList():
        for gpio in Gpio._usedGpio:
            print(gpio)


    @classmethod
    def eventHandler(c):
        while (1):
            Task.sleep()
            poll_list = c.poll.poll(100)
            if not len(poll_list):
                continue

            for poll_ret in poll_list:
                fd = poll_ret[0]
                gpio = c.gpioByFd(fd)
                prevVal = gpio.prevVal
                val = gpio.value()
                gpio.prevVal = val
                if gpio.eventCb:
                    gpio.eventCb(gpio, val, prevVal)


    @classmethod
    def startEvents(c):
        c.task.setCb(c.eventHandler)
        c.task.start()


    @classmethod
    def stopEvents(c):
        c.task.stop()


