import threading


class AveragerQueueEmptyError(Exception):
    pass


class AveragerQueue():
    def __init__(s, size=0, queue=[]):
        s.size = size
        s.lock = threading.Lock()
        s.clear()
        s._q = queue

    def push(s, val):
        with s.lock:
            s._q.append(val)
            if s.size and (len(s._q) > s.size):
                s._q = s._q[1:]


    def round(s):
        with s.lock:
            s._q.sort()
            if not len(s._q):
                raise AveragerQueueEmptyError()
            return s._q[int((len(s._q) / 2) - 1)]


    def clear(s):
        with s.lock:
            s._q = []