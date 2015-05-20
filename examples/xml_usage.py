import sys
from textwrap import dedent

from twisted.web import server, resource
from twisted.internet import reactor, defer
from twisted.web.client import Agent, readBody
from twisted.web.http_headers import Headers

from txrest.xml import XmlResource
from txrest.mixin import FormEncodedPost

# Get an etree from one of the many libraries that provides it.
try:
    from lxml import etree
except ImportError:
    try:
        # Python 2.5-2.7+ (Built-In)
        import xml.etree.ElementTree as etree
    except ImportError:
        # normal ElementTree install
        import elementtree.ElementTree as etree

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
                <a href="basic">Xml Basic (rest method)</a><br>
                <a href="xml">Xml Deferred</a><br>
                <a href="rest">Xml Catchall (rest method)</a><br>
                <a href="form">Xml Post (mixin)</a><br>
            </body>      
        </html>'''


class RestBasic(XmlResource):
    """
    return xml from a rest method. (simple)
    """
    
    def rest_GET(self, request):
        element = etree.Element('example')
        element.attrib['is_example'] = 'True'
        element.text = "Hello World!"
        return element

class RestDeferred(XmlResource):
    """
    Xml REST resource using our helpers - we support returning a deferred.
    This allows you to use the decorator ``defer.inlineCallbacks``.
    """
    isLeaf = True

    @defer.inlineCallbacks
    def rest_GET(self, request):
        """
        Handle get requests, for examples sake, we have deferred
        processing that gets the contents of the web page example.com
        
        We then return an xml Element object.
        """
        agent = Agent(reactor)
        result = yield agent.request('GET', 'http://example.com/')
        body = yield readBody(result) # get the  contents of the page.
        root = etree.Element('example-dot-com')
        root.text = str(body)
        defer.returnValue(root)
        
    def rest_POST(self, request, post):
        # post is an Element object
        xml = dedent('''
            <addedToYourPost>
                <asdf>This is some text woohoo!</asdf>
                <note>This xml was inserted to whatever you posted!</note>
            </addedToYourPost>
        ''').strip()
        # add the element above to the post xml tree at the beginnging.
        post.insert(0, etree.fromstring(xml))
        
        # return post!
        return post
        
class RestCatchAll(XmlResource):
    """
    The rest method will receive all requests... regardless of the
    HTTP method/verb used.
    """
    isLeaf = True

    def rest(request, *args):
        return etree.Element('CatchAll')
        
class Form(resource.Resource):
    
    isLeaf = True
    
    def render_GET(self, request):
        return """
        <html>
            <body>
                <form action="form-post" method="post">
                <input type=text name="arg1" value="hello world" />
                <input type="submit" value="Submit">
                </form>
            </body>
        </html>
        """
        
@FormEncodedPost.mixin
class HandleFormPost(XmlResource):
    """
    In this example we use a mixin to handle a form-encoded post.
    While still getting the automation of xml handling when
    the content-type does not indicate a form post.
    
    Normally we expect 
    """
    isLeaf = True
    
    def rest_POST(self, request, post):
        root = etree.Element('example')
        root.text = 'hello world --- form args: %s' % str(post)
        return root
        
# Setup a resource heirarchy using 'putChild' - notice how XmlResource() plays
# nicely with regular resource.Resource() objects.
PORT = 8080
res = Root()
res.putChild('basic', RestBasic())
res.putChild('xml', RestDeferred())
res.putChild('rest', RestCatchAll())
res.putChild('form', Form())
res.putChild('form-post', HandleFormPost())
site = server.Site(res)
reactor.callLater(1, sys.stdout.write, 'Listening at http://localhost:%s\n' % PORT)
reactor.listenTCP(PORT, site)
reactor.run()
