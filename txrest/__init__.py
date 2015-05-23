"""
Contains constants and abstract classes for Rest interfaces defined in twisted.

Rest interfaces of different data-types (JSON / XML) have interface similarities and
those are documented in ``txrest.RestResource``.
"""

from os.path import abspath
import time
import traceback
import codecs
from unicodedata import normalize
from textwrap import dedent
import inspect

from twisted.web import server, resource, static
from twisted.internet import reactor
from twisted.internet.defer import Deferred, maybeDeferred, CancelledError, _DefGen_Return
from twisted.web.http import (INTERNAL_SERVER_ERROR, SERVICE_UNAVAILABLE, BAD_REQUEST)
from twisted.web.error import UnsupportedMethod
from twisted.internet.error import (ConnectionDone, ConnectionLost, ConnectionAborted)
from twisted.python.reflect import prefixedMethodNames
from twisted.python import log
from twisted.python.compat import intToBytes


REST_METHOD = 'rest'
REST_METHOD_PREFIX = 'rest_'
DEFAULT_ENCODING = 'utf-8'

RECURSION_DEPTH = 5 # the IETF suggests an HTTP redirect limit of 5 (this is a similar concept)

class ResourceRecursionLimit(Exception):
    """
    Raised when too many Resources have been returned from other Resources.
    """
    pass
    

class RestResource(resource.Resource, object):
    """
    RestResource is a Twisted Resource() object that can be used with the
    twisted eco-system.  RestResource is meant to be an abstract class
    that can be used to implement your own rest-like resource types.
    
    See ``txrest.json.JsonResource`` for an implemented example.
    
    When you implement a **RestResource()** class it should look like this::
    
    The ``render_*`` methods have been replaced with ``rest_*`` to
    distinguish between our methods, and the super-classes methods.
    
    The resolution of methods, and errors is handled in this abstract class.
    This replaces logic to handle all render methods, and then call
    rest, rest_GET, rest_POST, rest_PUT, rest_DELETE methods
    
    To implement a subclass/interface you must define a resource class first
    with a signature similar to ``class JsonResource(RestResource):``
    
    Next you must define these **class attributes**
    
    :ACCEPT: The accept header that will be returned to clients.
    :CONTENT_TYPE: The content type header that will be returned to clients...
                   must contain a ``%s`` where encoding should appear such as:
                   ``application/json; charset=%s``
    :HANDLE_TYPES: A tuple or list of types we will handle.
    :ERROR_CLASS: A class reference to twisted.web.resource.ErrorPage or a 
                  subclass thereof
    
    Next you must define these functions:
    
    ``def _format_post(self, request, body, encoding):`` - receives a string (body) and a desired internal
    encoding (encoding) and should return a data-object that is expected by the 
    second argument in ``rest_POST(request, post_data)`` definitions.
    
    ``def _format_response(self, request, response, encoding):`` - receives a data-type defind in the
    class attribute ``HANDLE_TYPES`` and serializes to a byte string that can be written to
    the client.  Encoding is the requested encoding of the resulting string.
    
    ---------------------------------------------------------------------------
    
    This class popualtes the request variable ``method_called`` to the name of 
    the method that was actually called to handle the request. 
    
    We populate the request variable ``recursion`` to an integer that keeps track of
    resource rendering recursion.
    
    We populate the request variable ``started`` to an epoch at the request start time.
    """
    
    # -- SUBCLASSES MUST IMPLEMENT THESE CLASS ATTRIBUTES ---------------------
    # ERROR_CLASS - a customized subclass of ``twisted.web.resource.ErrorPage``
    # ACCEPT - a bytes string defining the ACCEPT header.
    # CONTENT_TYPE - a bytes string defining the CONTENT_TYPE header.
    # HANDLE_TYPES - a sequence containing the response types that the subclass will
    #                parse and serialize.
    SUBCLASS_ATTRS = ('ACCEPT', 'CONTENT_TYPE', 'HANDLE_TYPES', 'ERROR_CLASS')
    
    def __init__(self, encoding=DEFAULT_ENCODING, *args, **kwargs):
        """
        :param encoding: (optional) string encoding to use for requests and responses.
        """
        self.encoding = encoding
        resource.Resource.__init__(self, *args, **kwargs)
        
        # check to make sure the encoding is valid
        # raises "LookupError: unknown encoding: bad-encoding"
        valid = codecs.lookup(encoding)
        
        # check to make sure the subclass has defind attributes
        for attr in self.SUBCLASS_ATTRS:
            if not hasattr(self, attr):
                raise ValueError(
                    '%s must implement the class attribute %s' % (self.__class__.__name__), attr)
    
    def render_HEAD(self, request):
        """
        The default behavior of HEAD for a REST api is to return an empty
        response.  If a browser performs a HEAD request against a REST API
        it can ignore the HEAD.  You are free to implement HEAD in your
        RestResource subclass if you need to handle it explicitly.
        
        return immediately - do not execute a GET() (default behavior)
        
        :param request: a ``twisted.web.server.Request`` instance
        """
        return ''
        
    def render(self, request):
        """
        Handle resource request normally, and then redirect the rendering to a
        ``rest_*`` method.
        
        :param request: a ``twisted.web.server.Request`` instance
        """
        # set json content type for response
        request.started = time.time()
        request.recursion = 0
        request.setHeader(b'accept', self.ACCEPT) # THIS GETS SET FROM SUPER CLASS
        request.setHeader(b'content-type', self.CONTENT_TYPE % self.encoding)
        fq_name = self.__module__ + '.' + self.__class__.__name__
        meth_name = REST_METHOD_PREFIX + str(request.method)
        method = getattr(self, meth_name, None)
        if not method:
            meth_name = REST_METHOD
            method = getattr(self, meth_name, None)
        if not method:
            # if the method requested doesn't exist we must respond to the client
            # with an exception that will fill out the proper header to conform
            # to the HTTP standard.
            if isinstance(getattr(self, 'allowedMethods', None), (list, tuple)):
                allowed_methods = self.allowedMethods
            else:
                allowed_methods = self._allowed_methods()
            raise UnsupportedMethod(allowed_methods) # ``twisted.web.server.Request`` handles this

        if not callable(method):
            err = "Resource (`%s.%s()`) is not callable" % (fq_name, meth_name)
            log.err(err)
            return self.ERROR_CLASS(INTERNAL_SERVER_ERROR, 'Resource Error', err, log=False).render(request)

        request.method_called = meth_name

        # --- HANDLE POST BODY ------------------------------------------------
        call_args = [request]
        body = None
        if request.method in ('POST', 'PUT'):
            # this is where we very carefully do the automatic handling
            # of post/put bodies.  We call the function that should be 
            # implemented to parse the content.
            try:
                body = request.content.read()
            except Exception as e:
                err = 'Failed reading HTTP BODY\n' + traceback.format_exc()
                log.err(err)
                return self.ERROR_CLASS(BAD_REQUEST, 'Malformed HTTP BODY', err, log=False).render(request)
            
            try:
                body_data = self._format_post(request, body, self.encoding)
            except Exception as e:
                err = 'Failed parsing HTTP BODY\n' + traceback.format_exc()
                log.err(err)
                return self.ERROR_CLASS(BAD_REQUEST, 'Malformed HTTP BODY', err, log=False).render(request)
            
            call_args.append(body_data)
            
            
        # -- Setup Response Callbacks -----------------------------------------
        # wrap the response in a maybeDeferred so we only
        # have one code path to deal with.
        df = maybeDeferred(method, *call_args)
        df.addCallback(self.on_response, request)
        df.addErrback(self.on_failure, request)

        # add a callback to be notified of early-connection-termination
        request.notifyFinish().addErrback(self.on_connection_closed, df, request)

        # return NOT_DONE_YET so the client connection isn't automatically closed.
        # this means we have to call request.finish() ourselves, which we'll do
        # in the ``on_response``, or ``on_failure`` methods.
        return server.NOT_DONE_YET

    def on_response(self, response, request):
        """
        Callback for the completion of a request
        This method is called after our rest_* method has been
        successfully called and has a result.
        
        :param response: Response from the RestResource().render()
                         This must be a Resource() instance or 
        :param request: ``twisted.web.server.Request`` instance
        """
        # handle succesful completion of http request
        # def render(self, resrc):
        if request.finished:
            # the request has already finished.  Most likely because the
            # client closed the connection early. Don't REPLY
            return

        fq_name = self.__module__ + '.' + self.__class__.__name__
        
        if isinstance(response, self.HANDLE_TYPES):
            # Check to see that our subclass has 
            try:
                # convert the response from a dictionary to a json string (encoded as utf-8)
                # note that this will handle unicode strings within the dict properly.
                rstr = self._format_response(request, response, self.encoding)
            except Exception as e:
                # handle the exception.
                debug = 'Resource: (%s) [%s] Output serialization failed\n%s' % (
                    fq_name, request.method_called, traceback.format_exc())
                log.err(debug)
                rstr = self.ERROR_CLASS(
                    INTERNAL_SERVER_ERROR, 'Resource Error', debug, log=False).render(request)
            # in this case we know the content-length of the reply, so set
            # the header so the response encoding doesn't become "chunked"
            request.setHeader(b'content-length', intToBytes(len(rstr)))
            request.write(rstr)
            # if we don't call finish the connection will be left open and the
            # response buffer won't be sent/flushed!
            request.finish()
             
        elif isinstance(response, resource.Resource):
            # if the application returns a resource, render the resource... or 
            # fail if we've rendered too many resources for this request already.
            # Note: this logic should handle receiving a RestResource, or 
            # just a raw resource.Resource
            # the IETF suggests an HTTP redirect limit of 5 (this is a similar concept)
            depth = request.recursion
            if depth >= RECURSION_DEPTH: 
                exc = ResourceRecursionLimit('Recursion Limit Exceeded [%i] (%s) at Resource (%s)' % (
                    depth, request.uri, fq_name))
                request.processingFailed(failure.Failure(exc)) # this will finish the request
            else:
                request.recursion += 1
                reactor.callLater(0, request.render, response)
                
        else:
            # If the response from the rest method isn't a serializable type, or resource
            # then we have a problem... and this is a big deal because there is
            # an unexpected failure condition within the Resource.
            debug = 'Resource (%s) [%s] returned unsupported type %s' % (
                fq_name, request.method_called, type(response))
            log.err(debug)
            response = self.ERROR_CLASS(
                INTERNAL_SERVER_ERROR, 'Resource Error', debug, log=False).render(request)
            request.write(response)
            request.finish()


    def on_failure(self, failure, request):
        """
        Handle exceptions raised during RestResource processing
        
        :param failure: ``twisted.python.failure.Failure`` instance
        :param request: ``twisted.web.server.Request`` instance
        """
        fq_name = self.__module__ + '.' + self.__class__.__name__
        file_path = abspath(inspect.getfile(self.__class__))

        if failure.check(CancelledError):
            # the request / deferred chain has been cancelled early.
            # doesn't matter if we respond no one is listening.
            rstr = err = 'Request was cancelled'
        elif failure.check(_DefGen_Return):
            failure.printBriefTraceback()
            err = dedent('''
                Received a Deferred Generator Response from Resource (%s)
                in the method:  [%s] ....................................
                This indicates you may be missing a yield statement and
                the decorator `@defer.inlineCallbacks`.
                File: %s
                
                If you do not have a yield statement, you should use a regular
                `return` statement and remove `defer.returnValue()`
            ''' % (fq_name, request.method_called, file_path)).strip()
            
            log.err(err + ' - ' + failure.getErrorMessage())
            rstr = self.ERROR_CLASS(
                        INTERNAL_SERVER_ERROR,
                        err,
                        failure.getErrorMessage(),
                        log=False
                   ).render(request)
        else:
            log.err('Exception in Resource (%s) [%s] <%s> - %s' % (fq_name, request.method_called, file_path, failure.getErrorMessage()))
            failure.printTraceback()
            rstr = self.ERROR_CLASS(
                        INTERNAL_SERVER_ERROR,
                        'Unhandled Error',
                        'Exception in Resource (%s) [%s] <%s> - %s' % (fq_name, request.method_called, file_path, failure.getTraceback()),
                        log=False
                   ).render(request)

        if request.finished:
            return
        
        request.write(rstr)
        request.finish()


    def on_connection_closed(self, reason, deferred, request):
        """
        Called in the event the connection is closed or an error
        happens before we can respond.
        
        This should be one of::
        
            twisted.internet.error.ConnectionDone     (they did it, cleanly)
                                   ConnectionLost     (we lost connection [not cleanly])
                                   ConnectionAborted  (we did it - too many connections?)
        """
        duration = round(time.time() - request.started, 4)
        if reason.check(ConnectionDone):
            # the client got sick of waiting on us and closed the connection
            log.msg('client hung up after %s secs' % duration)
        elif reason.check(ConnectionLost):
            log.msg('lost connection after %s secs' % duration)
        elif reason.check(ConnectionAborted):
            log.msg('server aborted connection after %s secs' % duration)
        
        deferred.cancel() # cancel queued operations (this will trigger self.on_failure)
                
    
    def _allowed_methods(self):
        """
        Compute allowable http methods to return in an Allowed-Methods header.
        This is to adhere to the HTTP standard.
        """
        allowed_methods = ['HEAD'] # we always allow head
        fq_name = self.__module__ + '.' + self.__class__.__name__
        name = '?'
        try:
            resource = self
            for n in prefixedMethodNames(resource.__class__, REST_METHOD_PREFIX):
                name = n
                allowed_methods.append(n.encode('ascii'))
        except UnicodeEncodeError:
            log.err('Resource (%s) method (%s) contains non-ascii characters' % (fq_name, name))
        except Exception as e:
            log.err('Resource (%s) error resolving method names (%s)' % (fq_name, e))
        return allowed_methods
       
       
       
    def _format_response(response, encoding):
        """
        Implemented by derived classes to handle a type defined in
        the class constant ``HANDLE_TYPES``.  Any type defined in
        this constant will be sent to this function.  The return
        value should be a bytes or string object that will be
        written to the client socket.
        """
        raise NotImplementedError()
       
    def _format_post(body, encoding):
        """
        Implemented by derived classes to handle POST or PUT bodies.
        The return value should be a data-structure that your 
        RestResource() classes will use.  Typically the return
        value is an XML object or a Python DICT or LIST parsed from
        a JSON byte string.
        
        :param body: a bytes or string object
        :param encoding: the desired encoding to encode the string as.
        """
        raise NotImplementedError() 
