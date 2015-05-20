"""
``txrest.json`` module.  Json Rest API interfaces are defined in this module.
"""

from __future__ import absolute_import
import json
from unicodedata import normalize
import logging

from twisted.python import log
from twisted.web import resource
from twisted.web.http import BAD_REQUEST

from txrest import RestResource, DEFAULT_ENCODING


ACCEPT_HEADER = b'application/json'
CONTENT_TYPE_HEADER = b'application/json; charset=%s'

class JsonErrorPage(resource.ErrorPage):
    """
    A custom version of ``twisted.web.resource.ErrorPage``
    
    Returns valid json documents instead of html, and checks for
    ``request.debug`` ... if present the ``detail`` argument is 
    shown to the client.  The detail argument should contain 
    private informate like exceptions, which is how I've organized
    the application thus far.
    
    **Use Cases**
       
    Call Format::
        
        ErrorPage(http_code, generic_message, detail_message)
        
    :Note: You should never share any information in the middle-argument that would
           alert someone that Python is being used as the backend, or that might leak any
           exception information, even the exception type.  The string sent should always
           be generic or ambigious to some level.
           
           The last argument *debug_message* can be specified in every situation. This
           class intenlligently decides when to actually return it to the client based on
           if ``request.site.displayTracebacks`` is True.
       
    When using error page from an Exception::
        
        import traceback
        try:
            raise RuntimeError('Something Went Wrong')
        except Exception:
            ErrorPage(500, "Server Error", traceback.format_exc())
            
    OR if the traceback isn't important, because its an expected error,
    you might just want to show the exception message::
        
        try:
            raise UnicodeDecodeError('`email` field invalid utf-8')
        except Exception as e:
            ErrorPage(500, "utf-8 Decoding Error", str(e))

    """

    def __init__(self, status, brief, detail, encoding=DEFAULT_ENCODING, log=True):
        """
        Note that the signature of this function and the names of the variables have been
        kept identical to the original version of this class.
        
        detail is conditionally shown 
        
        :param status: Http Status Code
        :param brief: Error Type
        :param detail: Error Description
        :param encoding: Encoding to use when sending response
        :param log: log the error to twisted logging mechanism.
        """
        # arguments are left identical to ErrorPage
        resource.Resource.__init__(self)
        
        self.code = status
        self.brief = brief
        self.detail = detail
        self.encoding = encoding
        self.log = log
        

    def render(self, request):
        """
        Format the exception and return a dictionary.
        """
        response = {
            "code": self.code,
            "error": self.brief.encode(self.encoding),
            "detail": unicode(self.detail).encode(self.encoding),
        }
        
        if not request.site.displayTracebacks:
            response['detail'] = None
            
        if self.log:
            # ensure strings get represented in the logs even with nonsense in them
            # (un-encodable strings get saved still)
            brief = normalize('NFKD', unicode(self.brief)).encode('ASCII', 'ignore')
            detail = normalize('NFKD', unicode(self.detail)).encode('ASCII', 'ignore')
                
            # ErrorPage: [500] Invalid Name - Expected int, 
            log.msg(
                "%s: [%s] %s - %s" % (self.__class__.__name__, self.code, brief, detail), 
                logLevel=logging.WARNING
            )
        
        request.setResponseCode(self.code)
        request.setHeader(b'accept', ACCEPT_HEADER)
        request.setHeader(b'content-type', CONTENT_TYPE_HEADER % self.encoding)
        # dump a dict to get correctly formatted json
        rstr = json.dumps(
            response,
            allow_nan=False,
            check_circular=False, 
            ensure_ascii=False, 
            encoding=self.encoding,
            # -- pretty-print --
            sort_keys=True,
            indent=4)
        return rstr
        
    def __str__(self):
        return "%s: [%s] %s - %s" % (self.__class__.__name__, self.code, self.brief, self.detail)



class JsonResource(RestResource):
    """
    JsonResource is a Twisted resource.Resource() object.
    
    JsonResource is a Twisted Resource() object that can be used with the
    twisted eco-system.  You can use a JsonResource() with a resources
    ``putChild()`` method.  You can pass a ``JsonResource()`` as the root resource to
    a twisted ``Site()`` object, etc.  Anywhere a Resource() class is used,
    JsonResource() can be used.
    
    When you implement a **JsonResource()** class it should look like this::
    
        from txrest.json import JsonResource
        
        class MyJsonResource(JsonResource):
        
            @defer.inlineCallbacks
            def rest_GET(self, request):
                def hello(*args):
                    print "hello from rest_GET!", args
                    
                yield reactor.callLater(1, hello, 'everyone')
                defer.returnValue({"hello": "world"})
                
            def rest_POST(self, request, post):
                # pass a raw dictionary to this method.
                post['note'] = "this is the post data-structure
                return post
    
    The ``render_*`` methods have been replaced with ``rest_*`` to
    distinguish between our methods, and the twisted resource methods.
    
    This replaces logic to handle all render methods, and then call
    rest, rest_GET, rest_POST, rest_PUT, rest_DELETE methods
    
    When you implement a ``rest_GET`` method it must accept at least one argument
    ``request`` which is a twisted Request object.
    
    When handling a post request, you must implement the method ``rest_POST``.
    The full signature should be: ``rest_POST(self, request, post)``.  The ``post``
    variable will be a dictionary or list encoded from the POST-JSON sent to the server.
    This system is very simple, it expects valid json to be sent to it, and returns
    valid json when you return a python dictionary from a rest_POST or rest_GET method.
    
    A rest_* method can return one of: a Deferred, a Resource, a List or a Dictionary.
    The Dictionary and List will automatically be encoded to JSON and returned.
    Because you can return deferred's from the rest method you can use the 
    ``deferred.inlineCallbacks`` decorator with the method to make your life easier.
    
    When sending a ``POST`` request the body must always be a JSON payload, even if it
    is an empty data structure such as: ``{}`` or ``[]``
    """
    ACCEPT = ACCEPT_HEADER
    CONTENT_TYPE = CONTENT_TYPE_HEADER
    HANDLE_TYPES = (dict, list, tuple)
    ERROR_CLASS = JsonErrorPage
    
    def _format_response(self, request, response, encoding):
        """
        When a type in HANDLE_TYPES is returned, the super-class (RestResource)
        will call this method.
        
        We are responsible for formatting the message to a string/bytes and returning it.
        The returned value wi0ll be output to the http-client.
        
        :param request: ``twisted.web.server.Request`` instance
        :param response: an object returned from a rest_* method.
                         this should be a json-encodable object: (dict, list, tuple)
        :param encoding: a string that describes the desired encoding to pass into
                         ``json.dumps(encoding='<encoding>')``
        """
        rstr = json.dumps(
            response,
            allow_nan=False, # strict compliance to JSON
            check_circular=False, # speedup
            ensure_ascii=False, # allows the result to be a UNICODE object.
            encoding=encoding
        ).encode(encoding)
        return rstr
        

    def _format_post(self, request, body, encoding):
        """
        Format the contents of a raw POST body.
        
        In the case of this JSON instance this is called by the abstract class
        to return a structured object that can be passed into your Resource.
        
        This is an internal function and should not be used directly.
        
        :param request: ``twisted.web.server.Request`` instance
        :param body: (bytes) a byte string that contains the post contents.
        :param encoding: a string that describes the desired encoding to pass into
                         ``json.loads(encoding='<encoding>')``
        """
        # a very quick test to deny malformed bodies.
        # TODO support flag for log_post ?
        char = body.lstrip()[0]
        if char not in ('{', '['):
            raise ValueError('Invalid JSON first character != { or [... \nGot: %s ...' % body[:60])

        # this will return strings as Unicode()
        body_data = json.loads(body, encoding=encoding)

        return body_data
