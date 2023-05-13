import re, datetime, random
from Task import *


class Cron():
    def __init__(s):
        s.task = Task.setPeriodic('cron', 5000, s.do)
        s._workers = []
        s.lastMinute = datetime.datetime.now().minute
        s._disabled = False
        s.log = Syslog("Cron")


    def do(s, task):
        if s._disabled:
            return

        now = datetime.datetime.now()
        if now.minute == s.lastMinute:
            return

        s.lastMinute = now.minute
        for wrk in s._workers:
            if wrk.math(now):
                def cb():
                    Task.sleep(random.randrange(1, 15) * 1000)
                    wrk.cb()
                try:
                    Task.asyncRun('cron_worker_%s' % wrk.name(), cb)
                except TaskAlreadyExistException:
                    s.log.err('Can`t start worker "%s", ' \
                              'previous execution is not finished' % wrk.name())


    def workers(s):
        return s._workers


    # rule like the crontab format: "* * * * *"
    #                    "minute hour day month dayOfWeek"
    # example: "*/5 14 * * *"
    def register(s, name, rule, cb):
        wrk = Cron.Worker(name, rule, cb)
        s._workers.append(wrk)


    def unregister(s, worker):
        s._workers.remove(worker)


    def enable(s):
        s._disabled = False


    def disable(s):
        s._disabled = True


    def __repr__(s):
        return ("Cron %s:\n%s" % ('disabled' if s._disabled else 'enabled', \
                                  ''.join(["\t%s\n" % str(w) for w in s.workers()])))




    class Worker():
        class Error(Exception):
            pass

        def __init__(s, name, rule, cb):
            s._name = name
            s.cb = cb
            s.parseRule(rule)
            s.rule = rule
            s._disabled = False


        def enable(s):
            s._disabled = False


        def disable(s):
            s._disabled = True


        def name(s):
            return "%s:%s" % (s._name, s.rule.replace(' ', '_'))


        def parseRule(s, rule):
            limits = [{'type': 'minutes', 'min': 0, 'max': 59},
                      {'type': 'hour', 'min': 0, 'max': 23},
                      {'type': 'day', 'min': 1, 'max': 31},
                      {'type': 'month', 'min': 1, 'max': 12},
                      {'type': 'dayOfWeek', 'min': 1, 'max': 7}]
            li = iter(limits)
            try:
                s.minutes, s.hours, s.days, \
                s.months, s.daysWeek = [s.parseItem(i.strip(), next(li))
                                      for i in rule.split(' ')
                                         if len(i.strip())]
            except ValueError as e:
                raise Cron.Worker.Error('wrong amount of items ' \
                                        '"%s": %s' % (item, e))


        def parseItem(s, item, limits):
            def parse(item):
                if item.find(',') > -1:
                    try:
                        return [int(i) for i in item.split(',')]
                    except ValueError as e:
                        raise Cron.Worker.Error('syntax error "%s": %s' % (item, e)) from e

                if item.find('-') > -1:
                    try:
                        start, end = [int(i) for i in item.split('-')]
                    except ValueError as e:
                        raise Cron.Worker.Error('syntax error "%s": %s' % (item, e)) from e
                    if start > end:
                        raise Cron.Worker.Error('item interval error: %s' % item)
                    return [i for i in range(start, end + 1)]

                if item == '*':
                    return None

                m = re.findall('\*/(\d+)', item)
                if len(m):
                    try:
                        return [i for i in range(limits['min'], limits['max'] + 1, int(m[0]))]
                    except ValueError as e:
                        raise Cron.Worker.Error('syntax error "%s": %s' % (item, e)) from e

                try:
                    return [int(item)]
                except ValueError as e:
                    raise Cron.Worker.Error('syntax error "%s": %s' % (item, e)) from e

            values = parse(item)
            if values != None:
                for i in values:
                    if i < limits['min']:
                        raise Cron.Worker.Error('incorect %s "%s" in list: %s' % (
                                                limits['type'], i, values))
                    if i > limits['max']:
                        raise Cron.Worker.Error('incorect %s "%s" in list: %s' % (
                                                limits['type'], i, values))
            return values


        def math(s, now):
            if s._disabled:
                return False
            if s.minutes and now.minute not in s.minutes:
                return False
            if s.hours and now.hour not in s.hours:
                return False
            if s.days and now.day not in s.days:
                return False
            if s.months and now.month not in s.months:
                return False
            if s.daysWeek and now.weekday() not in s.daysWeek:
                return False
            return True


        def __repr__(s):
            return "Cron.%s:%s" % (s.name(), 'disabled' if s._disabled else 'enabled')


        def __str__(s):
            return "Cron.%s:%s" % (s.name(), 'disabled' if s._disabled else 'enabled')

