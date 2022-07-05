import os, math, datetime


class FileError(Exception):
    pass

def filePutContent(filename, data):
    try:
        with open(filename, "w") as f:
            f.write(data)
            f.flush()
    except Exception as e:
        raise FileError("filePutContents(%s) error: %s" % (filename, e)) from e


def fileGetContent(filename):
    try:
        with open(filename, "r") as f:
            data = f.read()
            return data
    except Exception as e:
        raise FileError("fileGetContent(%s) error: %s" % (filename, e)) from e


def fileGetBinary(filename):
    try:
        with open(filename, "rb") as f:
            data = f.read()
            return data
    except Exception as e:
        raise FileError("fileGetBinary(%s) error: %s" % (filename, e)) from e


def timeDurationStr(duration):
    if duration == None:
        return None
    totalMins = math.floor(duration / 60)
    totalHours = math.floor(totalMins / 60)

    days = math.floor(totalHours / 24)
    hours = totalHours - days * 24
    mins = totalMins - totalHours * 60
    sec = duration - totalMins * 60

    str = "%02d" % sec
    if mins:
        str = "%02d:%s" % (mins, str)
    if hours:
        str = "%02d:%s" % (hours, str)
    if days:
        str = "%dd %s" % (days, str)
    return str


def timeDateToStr(timestamp):
    if timestamp == None:
        return None
    d = datetime.datetime.fromtimestamp(timestamp)
    return "%02d.%02d.%04d %02d:%02d:%02d" % (d.day, d.month, d.year, d.hour, d.minute, d.second)

