import threading


class AveragerQueueEmptyError(Exception):
    pass


class AveragerQueue():
    def __init__(s, size=0, queue=None):
        s.size = size
        s.lock = threading.Lock()
        s.clear()
        s._q = []
        if queue:
            s._q = queue


    def push(s, val):
        with s.lock:
            s._q.append(val)
            if s.size and (len(s._q) > s.size):
                s._q.pop(0)

    def round(s):
        with s.lock:
            q = sorted(s._q)
            if not len(q):
                raise AveragerQueueEmptyError()
            return q[int((len(q) / 2) - 1)]


    def clear(s):
        with s.lock:
            s._q = []


    def __repr__(s):
        return "AveragerQueue/len:%d" % len(s._q)
