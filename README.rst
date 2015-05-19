txrest
======
TxRest provides a suite of Resources to implement **Restful** apis in Twisted.

The api is implemented by exposing custom Resource() classes.
Rest-Resources behave almost identical to ``Twisteds`` ``resource.Resource()`` classes.

The major difference is we support returning a **deferred** and you use the methods 
``rest_GET``, ``rest_POST``... instead of ``render_GET`` and render_POST``.

Restful JSON
============
To implement a restful JSON client we'll be using the ``txrest.json.JsonResource`` class.

**Quickstart (Simple)**::

        from txrest.json import 
        class MyJsonResource(JsonResource):
            isLeaf = True

            def rest(self, request, post=None):
                # For all Methods return hello world JSON
                defer.returnValue({"hello": "world"})
                
        site = server.Site(MyJsonResource())
        reactor.listenTCP(8080, site)
        reactor.run()

**Quickstart (GET)**::

        from txrest.json import 
        class MyJsonResource(JsonResource):
            isLeaf = True
 
            @defer.inlineCallbacks
            def rest_GET(self, request):
                _ = yield reactor.callLater(1, hello, 'everyone')
                defer.returnValue({"hello": "world"})
                
        site = server.Site(MyJsonResource())
        reactor.listenTCP(8080, site)
        reactor.run()
 
**Quickstart (POST)**::
            
        from txrest.json import 
        class MyJsonResource(JsonResource):
            isLeaf = True
 
            @defer.inlineCallbacks
            def rest_POST(self, request, post):
                # post should be a dictionary or a list
                post['hello'] = 'world'
                _ = yield reactor.callLater(1, lambda: True)
                defer.returnValue(post)  # return the contents of what we posted.
                
        site = server.Site(MyJsonResource())
        reactor.listenTCP(8080, site)
        reactor.run()
            
Standard vs TxRest Comparison
-----------------------------
This is a comparison of the standard way, vs our way...

The goal is to return the contents of `example.com` in a JSON response object.

**Standard Way**::

    class NormalDeferred(resource.Resource):
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
                # which is also an async operation.
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
        
**Using TxRest**::

    class RestDeferred(JsonResource):
        isLeaf = True

        @defer.inlineCallbacks
        def rest_GET(self, request):
            agent = Agent(reactor)
            result = yield agent.request('GET', 'http://example.com/')
            body = yield readBody(result) # get the  contents of the page.
            defer.returnValue({'web-request': str(body)})
        
Hopefully from the above example it's clear that automating the encoding, and decoding
of responses and POST bodies to JSON types offers a fair amount of conveniance.

In addition we support returning resources from the ``rest_*`` methods, which means 
you can return a Resource object as a response.


Handling Errors in your Resource
--------------------------------
Twisted has a built in version of an "error page" ``twisted.web.resource.ErrorPage`` 
that sets the http response code for you and formats an error.  
This page is returned whenever there is an unhandled exception.

Unhandled exceptions will automatically return an error page for you.  But it's useful to
use this Resource yourself.

In addition to returning an error response, ``JsonErrorPage`` will log to twisteds log
the error as well.  This can be prevented by passing log=False to the constructor, but typically
this functionality is useful.

**Return 400 Bad Request**::


    from twisted.web.http import BAD_REQUEST
    from txrest.json import JsonResource, JsonErrorPage

    class RestDeferred(JsonResource):
        isLeaf = True

        @defer.inlineCallbacks
        def rest_GET(self, request):
        
            if 'argument' not in request.args:
                return JsonErrorPage(BAD_REQUEST, '`argument` missing', 'additional info')
        
            agent = Agent(reactor)
            result = yield agent.request('GET', 'http://example.com/')
            body = yield readBody(result)
            defer.returnValue({'web-request': str(body)})
