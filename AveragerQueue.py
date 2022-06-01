
class AveragerQueue():
    def __init__(s, size=0):
        s.size = size
        s.clear()

    def push(s, val):
        s._q.append(val)
        if s.size and (len(s._q) > s.size):
            s._q = s._q[1:]


    def round(s):
        s._q.sort()
        return s._q[int((len(s._q) / 2) - 1)]


    def clear(s):
        s._q = []