import threading
import socket
import select
import json
from Task import *
from Syslog import *


class HttpHandlerError(Exception):
    def __init__(s, msg, errCode=""):
        s.errCode = errCode
        super().__init__(msg)


    def code(s):
        return s.errCode

class HttpConnection(Exception):
    pass

class HttpConnectionHeaderError(HttpConnection): # Needed header is absent
    pass

class HttpConnectionCookieError(HttpConnection): # Needed cookie is absent
    pass

class HttpConnectionBodyError(HttpConnection): # Needed cookie is absent
    pass


class HttpServer():
    def __init__(s, host, port, wwwDir = None):
        s._host = host
        s._port = port
        s._wwwDir = wwwDir
        s._listenedSock = None
        s._connections = []
        s._lock = threading.Lock()

        s._task = Task('http_server_%s:%d' % (host, port), s.taskDo)
        s._task.start()
        s._reqHandlers = []


    def setReqHandler(s, method, url, cb, requiredFields=[], retJson=True, errLog=False):
        reqHandler = HttpServer.ReqHandler(method, url, cb, requiredFields, retJson, errLog)
        s._reqHandlers.append(reqHandler)
        return reqHandler


    def reqHandlers(s):
        return s._reqHandlers


    def wwwDir(s):
        return s._wwwDir


    def connections(s):
        return s._connections


    def taskDo(s):
        s._listenedSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s._listenedSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s._listenedSock.bind((s._host, s._port))
        s._listenedSock.settimeout(1.0)
        s._listenedSock.listen(50)
        while 1:
            Task.sleep(0)
            while 1:
                Task.sleep(0)
                try:
                    conn, addr = s._listenedSock.accept()
                except socket.error:
                    continue
                break

            if not s._listenedSock:
                return

#            conn.settimeout(30)
            httpConn = HttpServer.Connection(s, conn, addr, s._wwwDir)
            with s._lock:
                s._connections.append(httpConn)
            httpConn.run()


    @staticmethod
    def parseHttpRequest(req):
        parts = req.split("\r\n\r\n")
        if not len(parts):
            return

        header = parts[0]
        body = None
        if len(parts) > 1:
            body = parts[1]

        lines = header.split("\n")
        if not len(lines):
            return None

        if not len(lines):
            return None

        parts = lines[0].split()
        if len(parts) != 3:
            return None

        method, url, version = parts

        attrs = []
        for line in lines[1:]:
            if not line.strip():
                continue

            row = line.split(":")
            name = row[0].strip()
            val = row[1].strip()
            attrs.append((name, val))

        return (method, url, version, attrs, body)


    @staticmethod
    def parseHttpResponce(resp):
        parts = resp.split("\r\n\r\n")
        if not len(parts):
            return

        header = parts[0]
        body = None
        if len(parts) > 1:
            body = parts[1]

        lines = header.split("\n")
        if not len(lines):
            return None

        if not len(lines):
            return None

        parts = lines[0].split()
        if len(parts) < 3:
            return None

        version = parts[0]
        code = parts[1]

        attrs = []
        for line in lines[1:]:
            if not line.strip():
                continue

            row = line.split(":")
            name = row[0].strip()
            val = row[1].strip()
            attrs.append((name, val))

        return (version, code, attrs, body)


    @staticmethod
    def parseParamsString(line):
        argsText = line.split("&")
        args = {}
        for keyVal in argsText:
            row = keyVal.split("=")
            if len(row) < 2:
                continue
            key, val = keyVal.split("=")
            args[key] = val
        return args


    def __repr__(s):
        msg = "HttpServer: %s:%s\n" % (s._host, s._port)
        for h in s._reqHandlers:
            msg += "\t%s\n" % h.url
        return msg


    def destroy(s):
        print("destroy HttpServer")
        s._task.remove()
        with s._lock:
            connections = s._connections

        for conn in connections:
            conn.close()
        s._listenedSock.shutdown(socket.SHUT_RDWR)
        s._listenedSock.close()
        s._listenedSock = None


    class ReqHandler():
        def __init__(s, method, url, handler, requiredFields, retJson, errLog):
            s.method = method
            s.url = url
            s.handler = handler
            s.requiredFields = requiredFields
            s.retJson = retJson
            s.errLog = errLog
            if errLog:
                s.log = Syslog("HttpServer.ReqHandler %s" % url)


        def match(s, method, url):
            return method == s.method and url == s.url


        def call(s, conn, args):
            for f in s.requiredFields:
                if f not in args:
                    return json.dumps({'status': 'error',
                                       'reason': "filed '%s' is absent in %s request" % (
                                       f, s.method)})

            try:
                ret = None
                ret = s.handler(args, conn)
                content = ret

                if s.retJson:
                    if not ret:
                        ret = {}
                    ret['status'] = 'ok'
                    content = json.dumps(ret)
                return content
            except HttpHandlerError as e:
                if s.errLog:
                    s.log.err("HttpHandlerError: %s" % e)
                return json.dumps({'status': 'error',
                                   'reason': '%s' % e,
                                   'errCode': e.code()})
            except TypeError as e:
                err = "Http subscriber %s return not seriable data.\n" \
                      "Error: %s.\n" \
                      "Data: %s" % (s.url, e, ret if ret else '')
                if s.errLog:
                    s.log.err(err)
                return json.dumps({'status': 'error',
                                   'reason': err})


        def __repr__(s):
            return "HttpServer.ReqHandler:%s" % s.url



    class Connection():
        def __init__(s, server, conn, remoteAddr, wwwDir = None):
            s._server = server
            s._conn = conn
            s._wwwDir = wwwDir
            s._remoteAddr = remoteAddr
            s._name = "%s:%d" % (remoteAddr[0], remoteAddr[1])
            s.log = Syslog("http_connection_%s:%d" % (remoteAddr[0], remoteAddr[1]))
            s.log.mute('debug')
            s.respHeaders = []
            s._keep_alive = False
            s._task = Task("http_connection_%s:%d" % (remoteAddr[0], remoteAddr[1]),
                           s.taskDo, autoremove=True)
            s._headers = []
            s._body = ""


        def name(s):
            return s._name


        def remoteAddr(s):
            return "%s:%s" % (s._remoteAddr[0], s._remoteAddr[1])


        def headers(s):
            return s._headers


        def header(s, name):
            for key, val in s._headers:
                if key == name:
                    return val
            raise HttpConnectionHeaderError('header %s has absent in request' % name)


        def body(s):
            return s._body


        def bodyJson(s):
            try:
                return json.loads(s._body)
            except json.decoder.JSONDecodeError as e:
                raise HttpConnectionBodyError("Can't parse body as JSON: %s. Body: %s" % (
                                                e, s._body))


        def setCookie(s, key, val, path='/', max_age=94608000):
            s.setHeader("Set-Cookie: %s=%s; path=%s; Max-Age=%s" % (key, val, path, max_age))


        def removeCookie(s, key):
            s.setHeader("Set-Cookie: %s=delete; Max-Age=-1" % key)


        def cookies(s):
            cookies = []
            for key, val in s.headers():
                if key != 'Cookie':
                    continue

                items = val.split(';')
                for item in items:
                    key, val = item.split('=')
                    cookies.append((key.strip(), val.strip()))
            return cookies


        def cookie(s, name):
            for key, val in s.cookies():
                if key == name:
                    return val
            raise HttpConnectionCookieError('cookie %s has absent in request' % name)


        def setHeader(s, row):
            s.respHeaders.append(row)


        def run(s):
            s._task.start()


        def task(s):
            return s._task


        def taskDo(s):
            with s._conn:
                poll = select.poll()
                poll.register(s._conn.fileno(), select.POLLIN)
                while 1:
                    Task.sleep(0)

                    poll_list = poll.poll(100)
                    if not len(poll_list):
                        continue

                    data = None;
                    try:
                        data = s._conn.recv(65535)
                    except:
                        pass

                    if not s._conn:
                        return

                    if (not data) or (not len(data)):
                        s.close()
                        return

                    try:
                        req = data.decode()
                    except:
                        s.close()
                        return

                    try:
                        parts = HttpServer.parseHttpRequest(req)
                    except IndexError:
                        parts = None

                    if not parts:
                        s.close()
                        return

                    method, url, version, s._headers, s._body = parts
                    s.log.debug("%s %s" % (method, url))
                    page, args = s.parseUrl(url)
                    if not args:
                        args = {}

                    try:
                        if s.header('Connection').lower() == 'keep-alive':
                            s._keep_alive = True
                    except HttpConnectionHeaderError:
                        pass

                    try:
                        if s.header('Content-Type') == 'application/x-www-form-urlencoded':
                            postArgs = HttpServer.parseParamsString(s._body)
                            args.update(postArgs)
                    except HttpConnectionHeaderError:
                        pass


                    requestProcessed = False
                    for reqHandler in s._server.reqHandlers():
                        if reqHandler.match(method, page):
                            requestProcessed = True
                            content = reqHandler.call(s, args)
                            break

                    if requestProcessed:
                        s.log.debug('response 200 OK')
                        s.respOk(content)
                    else:
                        if not s._wwwDir:
                            s.log.debug('url %s: 404 ERROR' % url)
                            s.resp404()

                        if url == '/':
                            url = 'index.html'

                        fileName = "%s/%s" % (s._wwwDir, url)
                        if not os.path.exists(fileName):
                            s.log.debug('url %s: 404 ERROR' % url)
                            s.resp404()
                        else:
                            content = fileGetBinary(fileName)
                            s.log.debug('response 200 OK, file "%s" is exist' % fileName)
                            mimeType = s.mimeTypeByFileName(fileName)
                            s.respOk(content, mimeType)

                    if s._keep_alive:
                        continue

                    s.close()
                    return

        def close(s):
            if not s._conn:
                return
            s._conn.close()
            s._conn = None
            s._task.remove()
            with s._server._lock:
                s._server._connections.remove(s)


        def mimeTypeByFileName(s, fileName):
            types = {"jpeg": "image/jpeg",
                     "jpg": "image/jpeg",
                     "png": "image/png",
                     "html": "text/html",
                     "htm": "text/html",
                     "js": "text/javascript",
                     "css": "text/css",
                     "txt": "text/plain",
                     };

            for type, mime in types.items():
                if fileName[-len(type):] == type:
                    return mime

            return "text/plain";


        def parseUrl(s, url):
            parts = url.split("?")
            if not parts:
                return None

            if len(parts) == 1:
                return (url, None)

            page = parts[0]
            args = HttpServer.parseParamsString(parts[1])
            return (page, args)


        def respOk(s, data = "", ctype = "text/plain"):
            if not s._conn:
                return

            if str(type(data)) == "<class 'str'>":
                data = data.encode('utf-8')

            header = "HTTP/1.1 200 OK\r\n"
            header += "Content-Type: %s\r\n" % ctype
            for row in s.respHeaders:
                header += "%s\r\n" % row
            header += "Content-Length: %d\r\n" % len(data)
            if s._keep_alive:
                header += "Connection: Keep-Alive\r\n"
            header += "\r\n"
            headerBytes = header.encode('utf-8')
            try:
                s._conn.send(headerBytes + data)
            except Exception as e:
                s.log.err("respOk error: %s" % e)
            s.respHeaders = []


        def respBadRequest(s, data = ""):
            if not s._conn:
                return
            if str(type(data)) == "<class 'str'>":
                data = data.encode('utf-8')

            header = "HTTP/1.1 400 Bad Request\r\n"
            header += "Content-Type: text/plain\r\n"
            header += "Content-Length: %d\r\n" % len(data)
            header += "\r\n"
            headerBytes = header.encode('utf-8')
            try:
                s._conn.send(headerBytes + data)
            except Exception as e:
                s.log.err("respBadRequest error: %s" % e)
            s.respHeaders = []


        def resp404(s):
            if not s._conn:
                return
            data = "404 Page not found".encode('utf-8')
            header = "HTTP/1.1 404 Page Not Found\r\n"
            header += "Content-Type: text/plain\r\n"
            header += "Content-Length: %d\r\n" % len(data)
            header += "\r\n"
            headerBytes = header.encode('utf-8')
            try:
                s._conn.send(headerBytes + data)
            except Exception as e:
                s.log.err("resp404 error: %s" % e)
            s.respHeaders = []


        def __repr__(s):
            return "HttpServer.Connection: %s" % s.name()



