from xml.etree import ElementTree

class SimpleXML():
    class Error(Exception):
        pass


    def __init__(s, xmlText):
        s.root = ElementTree.XML(xmlText)
        s._text = xmlText


    def xml(s):
        return s._text


    def toDict(s):
        return s.recurciveDict(s.root)


    def recurciveDict(s, root):
        if len(root):
            return {root.tag: {k: v for d in map(s.recurciveDict, root)
                                    for k,v in d.items()}}
        else:
            return {root.tag: root.text}

    def node(s, path):
        parts = path.split('/')
        if s.root.tag != parts[0]:
            raise SimpleXML.Error('Item "%s" not found in path "%s"' % (s.root.tag, path))

        parts = parts[1:]
        if not parts:
            return s.root

        node = s.root
        for part in parts:
            found = False
            for it in node:
                if it.tag == part:
                    node = it
                    found = True
                    break

            if not found:
                raise SimpleXML.Error('Item "%s" not found in path "%s"' % (part, path))
        return node


    def list(s, path):
        node = s.node(path)
        return [s.recurciveDict(n) for n in node]


    def item(s, path):
        node = s.node(path)
        return s.recurciveDict(node)[node.tag]



