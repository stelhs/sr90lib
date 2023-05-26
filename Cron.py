import re, datetime, random
from common import *
from Task import *


class Cron():
    class Err(Exception):
        pass

    def __init__(s):
        s.taskExec = Task('cronExec', s.execTask)
        s._workers = []
        s.lastStamp = now()
        s._disabled = False
        s.log = Syslog("Cron")
        s.taskExec.start()
        s.taskObserver = Task.setPeriodic('cronObserver', 300, s.timeObserver)


    def timeObserver(s, task):
        if s._disabled:
            return

        stamp = now()
        if stamp == s.lastStamp:
            return
        s.lastStamp = stamp
        s.taskExec.sendMessage(stamp)


    def execTask(s):
        while 1:
            stamp = s.taskExec.waitMessage()
            now = datetime.datetime.fromtimestamp(stamp)
            for wrk in s._workers:
                if wrk.isDisabled():
                    continue
                if wrk.math(now):
                    wrk.run()


    def workers(s):
        return s._workers


    def worker(s, name):
        for w in s.workers():
            if w.name() == name:
                return w
        raise Cron.Err('Worker "%s" is not registred' % name)


    # rulesStr: list of rule like the crontab format: "* * * * * *"
    #                                         "sec minute hour day month dayOfWeek(1-7)"
    # example: "* */5 14 * * *"
    def register(s, name, rulesStr, sync=False, precision=15):
        wrk = Cron.Worker(name, rulesStr, sync, precision)
        s._workers.append(wrk)
        return wrk


    def unregister(s, worker):
        s._workers.remove(worker)


    def enable(s):
        s._disabled = False


    def disable(s):
        s._disabled = True


    def printList(s, wildcard='*'):
        print("Cron %s:\n%s" % ('disabled' if s._disabled else 'enabled', \
                                  '\n'.join(["\t%s" % str(w) for w in s.workers()
                                              if wildcardMatch(wildcard, w.name())])))

    def __repr__(s):
        return ("Cron %s:\n%s" % ('disabled' if s._disabled else 'enabled', \
                                  '\n'.join(["\t%s" % str(w) for w in s.workers()])))



    class Worker():
        def __init__(s, name, rulesStr, sync, precision):
            s._name = name
            s.syncFlag = sync
            s.precision = precision
            s.cbList = []
            s.rules = [Cron.Rule(ruleStr) for ruleStr in rulesStr]
            s._disabled = False
            s.cntRun = 0
            s._historyCall = []


        def name(s):
            return s._name


        def enable(s):
            s._disabled = False


        def disable(s):
            s._disabled = True


        def isDisabled(s):
            return s._disabled


        def addCb(s, cb):
            s.cbList.append(cb)


        def run(s):
            s.cntRun += 1
            s._historyCall.append(now())
            if len(s._historyCall) > 100:
                s._historyCall = s._historyCall[-100:]

            if s.syncFlag:
                for cb in s.cbList:
                    cb(s)
                return

            def taskCb():
                Task.sleep(random.randrange(0, s.precision + 1) * 1000)
                for cb in s.cbList:
                    cb(s)
            try:
                s._task = Task.asyncRun('cron_worker_%s' % s.name(), taskCb)
            except TaskAlreadyExistException:
                s.log.err('Can`t start worker "%s", ' \
                          'previous execution is not finished' % s.name())


        def math(s, datetime):
            for r in s.rules:
                if r.math(datetime):
                    return True
            return False


        def printHistoryCall(s):
            times = [datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S')
                     for t in s._historyCall]
            print("\n".join(times))



        def __repr__(s):
            return "Cron.%s:%s:%s:%d" % (s.name(), ','.join([r.string() for r in s.rules]),
                                      'disabled' if s._disabled else 'enabled', s.cntRun)


        def __str__(s):
            return "Cron.%s:%s:%s:%d" % (s.name(), ','.join([r.string() for r in s.rules]),
                                      'disabled' if s._disabled else 'enabled', s.cntRun)



    class Rule():
        def __init__(s, ruleStr):
            s._ruleStr = ruleStr
            try:
                s.seconds, s.minutes, s.hours, s.days, \
                           s.months, s.daysWeek = s.parse(ruleStr)
            except ValueError as e:
                raise Cron.Err('wrong amount of items: %s' % e)


        def string(s):
            return s._ruleStr.replace(' ', '_')


        def parse(s, ruleStr):
            limits = [{'type': 'seconds', 'min': 0, 'max': 59},
                      {'type': 'minutes', 'min': 0, 'max': 59},
                      {'type': 'hour', 'min': 0, 'max': 23},
                      {'type': 'day', 'min': 1, 'max': 31},
                      {'type': 'month', 'min': 1, 'max': 12},
                      {'type': 'dayOfWeek', 'min': 1, 'max': 7}]
            li = iter(limits)
            return [s.parseItem(i.strip(), next(li))
                                  for i in ruleStr.split(' ')
                                     if len(i.strip())]


        def parseItem(s, item, limits):
            def parse(item):
                if item.find(',') > -1:
                    try:
                        return [int(i) for i in item.split(',')]
                    except ValueError as e:
                        raise Cron.Err('syntax error "%s": %s' % (item, e)) from e

                if item.find('-') > -1:
                    try:
                        start, end = [int(i) for i in item.split('-')]
                    except ValueError as e:
                        raise Cron.Err('syntax error "%s": %s' % (item, e)) from e
                    if start > end:
                        raise Cron.Err('item interval error: %s' % item)
                    return [i for i in range(start, end + 1)]

                if item == '*':
                    return None

                m = re.findall('\*/(\d+)', item)
                if len(m):
                    try:
                        return [i for i in range(limits['min'], limits['max'] + 1, int(m[0]))]
                    except ValueError as e:
                        raise Cron.Err('syntax error "%s": %s' % (item, e)) from e

                try:
                    return [int(item)]
                except ValueError as e:
                    raise Cron.Err('syntax error "%s": %s' % (item, e)) from e

            values = parse(item)
            if values != None:
                for i in values:
                    if i < limits['min']:
                        raise Cron.Err('incorect %s "%s" in list: %s' % (
                                                limits['type'], i, values))
                    if i > limits['max']:
                        raise Cron.Err('incorect %s "%s" in list: %s' % (
                                                limits['type'], i, values))
            return values


        def math(s, datetime):
            if s.seconds and datetime.second not in s.seconds:
                return False
            if s.minutes and datetime.minute not in s.minutes:
                return False
            if s.hours and datetime.hour not in s.hours:
                return False
            if s.days and datetime.day not in s.days:
                return False
            if s.months and datetime.month not in s.months:
                return False
            if s.daysWeek and (datetime.weekday() + 1) not in s.daysWeek:
                return False
            return True


        def __repr__(s):
            return "Cron.Rule:%s" % s.string()


        def __str__(s):
            return "Cron.Rule:%s" % s.string()



