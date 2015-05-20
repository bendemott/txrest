"""
This module implements XML-based Rest Resource Endpoint handling.
"""
from __future__ import absolute_import
from textwrap import dedent
try:
    from lxml import etree
except ImportError:
    try:
        # Python 2.5
        import xml.etree.cElementTree as etree
    except ImportError:
        try:
            # Python 2.5-2.7+ (Built-In)
            import xml.etree.ElementTree as etree
        except ImportError:
            try:
                # normal cElementTree install
                import cElementTree as etree
            except ImportError:
                # normal ElementTree install
                import elementtree.ElementTree as etree
                    

from unicodedata import normalize
import logging

from twisted.python import log
from twisted.web import resource
from twisted.web.http import BAD_REQUEST

from txrest import RestResource, DEFAULT_ENCODING

'''
we don't know which element type the client will be using,
they could be using a mixture of element types possibly
so we need to account for all of the element types here.
'''
ELEMENT_TYPES = []
try:
    from lxml import etree as _e1
    ELEMENT_TYPES.append(_e1.Element('e').__class__)
except ImportError:
    pass
    
try:
    # Python 2.5-2.7+ (Built-In)
    import xml.etree.ElementTree as _e3
    ELEMENT_TYPES.append(_e3.Element('e').__class__)
except ImportError:
    pass
    
try:
    # normal cElementTree install
    import cElementTree as _e4
    ELEMENT_TYPES.append(_e4.Element('e').__class__)
except ImportError:
    pass

try:
    # normal ElementTree install
    import elementtree.ElementTree as _e5
    ELEMENT_TYPES.append(_e5.Element('e').__class__)
except ImportError:
    pass


ACCEPT_HEADER = b'application/xml'
CONTENT_TYPE_HEADER = b'application/xml; charset=%s'

class XmlErrorPage(resource.ErrorPage):
    """
    Xml Error Page provides error responses and sets HTTP status codes for you.
    """
    
    XML_TEMPLATE = dedent('''
    <?xml version="1.0"?>
    <ErrorPage>
        <code></code>
        <brief></brief>
        <detail></detail>
    </ErrorPage>
    ''').strip()

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
        
        detail = self.detail
        if not request.site.displayTracebacks:
            detail = None
            
        if self.log:
            # ensure strings get represented in the logs even with nonsense in them
            # (un-encodable strings get saved still)
            brief = normalize('NFKD', unicode(self.brief)).encode(self.encoding, 'ignore')
            detail = normalize('NFKD', unicode(self.detail)).encode(self.encoding, 'ignore')
                
            # ErrorPage: [500] Invalid Name - Expected int, 
            log.msg(
                "%s: [%s] %s - %s" % (self.__class__.__name__, self.code, brief, detail), 
                logLevel=logging.WARNING
            )
        
        response = etree.fromstring(self.XML_TEMPLATE)
        response.xpath('//code')[0].text = str(self.code)
        response.xpath('//brief')[0].text = self.brief
        response.xpath('//detail')[0].text = detail
        
        request.setResponseCode(self.code)
        request.setHeader(b'accept', ACCEPT_HEADER)
        request.setHeader(b'content-type', CONTENT_TYPE_HEADER % self.encoding)
        # serialize xml object to string for output.
        rstr = etree.tostring(response, pretty_print=True)
        return rstr
        
    def __str__(self):
        return "%s: [%s] %s - %s" % (self.__class__.__name__, self.code, self.brief, self.detail)
    
class XmlResource(RestResource):
    """
    Xml Rest Resource.  Accepts XML Post Bodies and returns XML responses.
    """
    ACCEPT = ACCEPT_HEADER
    CONTENT_TYPE = CONTENT_TYPE_HEADER
    HANDLE_TYPES = tuple(ELEMENT_TYPES)
    ERROR_CLASS = XmlErrorPage
    

    def _format_post(self, request, body, encoding):
        """
        Format the contents of a raw POST body.
        
        In the case of this XML instance this is called by the abstract class
        to return a structured object that can be passed into your Resource.
        
        This is an internal function and should not be used directly.
        
        :param request: ``twisted.web.server.Request`` instance
        :param body: (bytes) a byte string that contains the post contents.
        :param encoding: a string that describes the desired encoding``
        """
        # a very quick test to deny malformed bodies.
        start = body.lstrip()[:5]
        if not start.startswith('<?xml'):
            raise ValueError('Invalid XML post body does not start with != <?xml... \nGot: %s ...' % body[:60])

        # parse the post body into an ElementTree object.
        body_data = etree.fromstring(body)
                
                
    def _format_response(self, request, response, encoding):
        """
        When a type in HANDLE_TYPES is returned, the super-class (RestResource)
        will call this method.
        
        We are responsible for formatting the message to a string/bytes and returning it.
        The returned value will be output to the http-client.
        
        :param request: ``twisted.web.server.Request`` instance
        :param response: an object returned from a rest_* method.
                         this should be an xml object: (xml.etree.ElementTree.Element, lxml.etree.Element, etc)
        :param encoding: a string that describes the desired encoding to pass into
                         ``etree.tostring(response, encoding=<encoding>)``
        """
        return etree.tostring(response, encoding=encoding)
