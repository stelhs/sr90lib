import requests, simplejson


class HttpClient():
    class Error(Exception):
        pass

    def __init__(s, name, host, port):
        s._host = host
        s._port = port
        s._name = name


    def reqGet(s, op, args = {}):
        url = "http://%s:%s/%s" % (s._host, s._port, op)
        try:
            r = requests.get(url = url, params = args)
            resp = r.json()
            if resp['status'] != 'ok' and resp['reason']:
                raise HttpClient.Error("Request '%s' to %s return response with error: %s" % (
                                op, s._name, resp['reason']))
            return resp
        except requests.RequestException as e:
            raise HttpClient.Error("Request '%s' to %s fails: %s" % (
                            op, s._name, e)) from e
        except simplejson.errors.JSONDecodeError as e:
            raise HttpClient.Error("Response for '%s' from %s parse error: %s. Response: %s" % (
                            op, s._name, e, r.content)) from e
        except KeyError as e:
            raise HttpClient.Error("Request '%s' to %s return incorrect json: %s" % (
                            op, s._name, r.content)) from e


    def reqPost(s, op, data, args = {}):
        url = "http://%s:%s/%s" % (s._host, s._port, op)
        try:
            r = requests.post(url=url, data=data, timeout=40, params = args,
                              headers={'Content-Type': 'application/x-www-form-urlencoded'})
            resp = r.json()
            if resp['status'] != 'ok' and resp['reason']:
                raise HttpClient.Error("Request '%s' to %s return response with error: %s" % (
                                op, s._name, resp['reason']))
            return resp
        except requests.exceptions.RequestException as e:
            raise HttpClient.Error('Request "%s" error: %s' % (op, e)) from e
        except KeyError as e:
            raise HttpClient.Error('Request "%s" error: Key %s is absent in responce' % (
                                       op, e)) from e