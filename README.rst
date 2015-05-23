txrest
======
TxRest provides a suite of Resources to implement **Restful** apis in Twisted.

The api is implemented by exposing custom Resource() classes.
Rest-Resources behave almost identical to ``Twisteds`` ``resource.Resource()`` classes.

The major difference is we support returning a **deferred** and you use the methods 
``rest_GET``, ``rest_POST``... instead of ``render_GET`` and ``render_POST``.

Restful JSON
============
To implement a restful JSON client we'll be using the ``txrest.json.JsonResource`` class.

**Quickstart (Simple)**:: python

    from twisted.internet import reactor
    from twisted.web import server
    from txrest.json import JsonResource
    
    class MyJsonResource(JsonResource):
        isLeaf = True

        def rest(self, request, post=None):
            # For all Methods return hello world JSON
            return {"hello": "world"}
            
    site = server.Site(MyJsonResource())
    reactor.listenTCP(8080, site)
    reactor.run()

**Quickstart (GET)**:: python

    import sys, time
    from twisted.internet import reactor, defer, task
    from twisted.web import server
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
 
**Quickstart (POST)**:: python
            
    import sys, time
    from twisted.internet import reactor, defer, task
    from twisted.web import server
    from twisted.python import log
    log.startLogging(sys.stdout)      
    from txrest.json import JsonResource
    
    class MyJsonResource(JsonResource):
        isLeaf = True

        @defer.inlineCallbacks
        def rest_POST(self, request, post):
            # post should be a dictionary or a list
            post['hello'] = 'world'
            _ = yield task.deferLater(reactor, 1, log.msg, 'the wait is over!')
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


    from twisted.internet import defer
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
            
            
            
Restful XML
===========
The Restful XML API is identical to the JSON api except it expects valid


**Basic XML Get**:: python

    import xml.etree.ElementTree as etree 
    from txrest.xml import XmlResource
    
    class RestBasic(XmlResource):
        """
        return xml from a rest method. (simple)
        """
        
        def rest_GET(self, request):
            element = etree.Element('example')
            element.attrib['is_example'] = 'True'
            element.text = "Hello World!"
            return element
        
**

Mixins
======
If you want to modify the way a particular resource you implement handles it's POST bodies
or it's responses we have mixins you can use that decorate your ``Resource`` class.

Mixins are located in the module ``txrest.mixins`` - They can be used with both ``JsonResource``
and ``XmlResource``

Here's a basic example that allows us to return non-standard responses, in this case
a string instead of an XML object.

:: python

    from txrest.xml import XmlResource
    from txrest.mixin import StringResponse

    @StringResponse.mixin
    class StringMixinTest(XmlResource):
        """
        Normally XmlResource() wants us to output an Element()
        object.  By decorating the resource we allow ourselves
        to return a byte string.
        """
        isLeaf = True
        
        def rest_GET(self, request):
            request.setHeader('content-type', 'text/plain')
            return "string response!"



