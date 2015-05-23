import json
import sys

from twisted.web import server, resource
from twisted.internet import reactor, defer
from twisted.web.client import Agent, readBody
from twisted.web.http_headers import Headers
from twisted.python import log
log.startLogging(sys.stdout)

from txrest.json import JsonResource, JsonErrorPage

class Root(resource.Resource):
    """
    A basic example, Twisteds built in resource handling.
    """
    isLeaf = False
    
    def getChild(self, name, request):
        if name == '':
            return self
        return resource.Resource.getChild(self, name, request)
    
    def render_GET(self, request):
        return '''
        <html>
            <body>
                <a href="normal">Normal Deferred</a><br>
                <a href="json">Json Deferred</a><br>
                <a href="rest">Json Catchall (rest method)</a><br>
                <a href="exception">Rest Exception</a><br>
                <a href="errorpage">JsonErrorPage test</a><br>
            </body>      
        </html>'''
        

class NormalDeferred(resource.Resource):
    """
    A regular resource example showing how to implement a json-rest resource
    without using our helpers...
    """
    isLeaf = True

    def render_GET(self, request):
    
        def fail(failure):
            request.write('we failed %s' % failure)
            request.finish()
    
        def return_body(body):
            """Called when we have a full response"""
            response = {'web-request': body}
            response = json.dumps(response, ensure_ascii=False, encoding='utf-8').encode('utf-8')
            request.write(body)
            request.finish()
    
        def get_body(result):
            # now that we have the body, 
            # we can return the result, using ready body
            # which is also a async operation.
            d2 = readBody(result) # get the  contents of the page.
            d2.addCallback(return_body)
            d2.addErrback(fail)
    
        # setup the deferred/callback for the first asynchronous 
        # call...
        agent = Agent(reactor)
        d1 = agent.request('GET', 'http://example.com/')
        d1.addCallback(get_body)
        d1.addErrback(fail)
        
        return server.NOT_DONE_YET


class RestDeferred(JsonResource):
    """
    Json REST resource using our helpers - we support returning a deferred.
    This allows you to use the decorator ``defer.inlineCallbacks``.
    """
    isLeaf = True

    @defer.inlineCallbacks
    def rest_GET(self, request):
        agent = Agent(reactor)
        result = yield agent.request('GET', 'http://example.com/')
        body = yield readBody(result) # get the  contents of the page.
        defer.returnValue({'web-request': str(body)})
        
    def rest_POST(self, request, post):
        post['note'] = 'Here is what you posted... returned to you!'
        return post
        
class RestCatchAll(JsonResource):
    """
    The rest method will receive all requests... regardless of the
    HTTP method/verb used.
    """
    isLeaf = True

    def rest(request, *args):
        return {'method': 'rest'}
        
  
class RestException(JsonResource):
    """
    Just raise an exception to show how uncaught exceptions are returned.
    """
    isLeaf = True

    def rest(request, *args):
        raise RuntimeError('test raising an error.')
        
        
class RestError(JsonResource):
    """
    The rest method will receive all requests... regardless of the
    HTTP method/verb used.
    """
    isLeaf = True

    def rest(request, *args):
        if True != False:
            return JsonErrorPage(
                500,
                "An Error Happened",
                "This error is your fault, here are more details"
            )
        else:
            return {'all': 'good'}
        
# Setup a resource heirarchy using 'putChild' - notice how JsonResource() plays
# nicely with regular resource.Resource() objects.
defer.setDebugging(True)
PORT = 8080
res = Root()
res.putChild('normal', NormalDeferred())
res.putChild('json', RestDeferred())
res.putChild('rest', RestCatchAll())
res.putChild('exception', RestException())
res.putChild('errorpage', RestError())
site = server.Site(res)
reactor.listenTCP(PORT, site)
reactor.callLater(0.1, sys.stdout.write, 'Listening at http://localhost:%s\n' % PORT)
reactor.run()
