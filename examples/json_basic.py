"""
Simple txrest.json Module usage using a deferred delay
to show the usage of inlineCallbacks
"""
import sys, time
from twisted.internet import reactor, defer, task
from twisted.web import server
from twisted.internet.task import deferLater
from twisted.python import log
log.startLogging(sys.stdout)
from txrest.json import JsonResource

class MyJsonResource(JsonResource):
    isLeaf = True

    @defer.inlineCallbacks
    def rest_GET(self, request):
        _ = yield task.deferLater(reactor, 1, log.msg, 'the wait is over!')
        defer.returnValue({"hello": "world %s" % time.time()})

defer.setDebugging(True)
site = server.Site(MyJsonResource())
reactor.listenTCP(8080, site)
reactor.run()
