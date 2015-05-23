import types
from txrest import RestResource

class ResourceMixin(object):
    """
    Base class for all mixins.
    
    Usage::
        
        @ResourceMixin.mixin
        class MixedResource(XmlResource):
            pass
            
    see: http://stackoverflow.com/questions/9539052/python-dynamically-changing-base-classes-at-runtime-how-to
    see: http://stackoverflow.com/questions/972/adding-a-method-to-an-existing-object
    """

    '''
    Define the names of the methods you want to overwrite.
    '''
    methods = []
    
    @classmethod
    def setup(cls, impl_cls):
        """
        Called when the function is decorated, you will be passed the 'impl_cls'
        instance which is the class you are decorating if you want to modify the class
        at the time of decoration.
        """
        pass
    
    @classmethod
    def mixin(cls, impl_cls):
        """
        Mixin methods dynamically to a Resource class instance.
        
        :param impl_cls: the class we are decorating
        """
        for meth_name in cls.methods:
            
            method = getattr(cls, meth_name, None)
            if method is None:
                raise ValueError("The method [%s] was defined as a mixin, "
                    "but is not implemented in the mixin class [%s]" % (meth_name, cls.__name__))
            # get the function, not the unbound method.
            func = cls.__dict__[meth_name]
            # replace the existing method on the class with our method.
            # setattr(impl_cls, meth_name, types.MethodType(impl_cls, method)) ( doesnt work )
            setattr(impl_cls, meth_name, func)
            
        cls.setup(impl_cls)
        return impl_cls
          

class EmptyPost(ResourceMixin):
    """
    Allow an empty POST BODY, by default
    
    ``JsonResource``, and ``XmlResource`` expect xml or json data structures.
    The structures themselves can be empty but the POST Body cannot.
    
    Introduce this Mixin as your First subclass when you write a Resource
    class to allow the Form post to be completely empty.
    
    The value of the ``post`` parameter passed into any function will be ``None``
    when empty, or white-space POST bodies are present.
    """
    methods = ['_format_post'] # override these methods if we are mixed in.
    
    def _format_post(self, request, body, encoding):
        """
        Forward request.args
        
        :param request: ``twisted.web.server.Request`` instance
        :param body: (bytes) a byte string that contains the post contents.
        :param encoding: a string that describes the desired encoding to pass into
                         ``json.loads(encoding='<encoding>')``
        """
        if not body.strip() or body is None:
            return None
        else:
            return super(self.__class__, self)._format_post(request, response, encoding)
        

class FormEncodedPost(ResourceMixin):
    """
    You can mixin this to any resource class you implement to handle 
    form encoded posts, instead of the default behavior of
    ``JsonResource`` or ``XmlResource``
    """
    WWW_FORM = 'application/x-www-form-urlencoded'
    FORM_DATA = 'multipart/form-data'
    methods = ['_format_post'] # override _format_post
    
    def _format_post(self, request, body, encoding):
        """
        Forward request.args to body
        
        :param request: ``twisted.web.server.Request`` instance
        :param body: (bytes) a byte string that contains the post contents.
        :param encoding: a string that describes the desired encoding to pass into
                         ``json.loads(encoding='<encoding>')``
        """
        content_type = request.getHeader('Content-Type')
        
        form_encoded = (True if (content_type == FormEncodedPost.WWW_FORM or
                        FormEncodedPost.FORM_DATA in content_type) else False)
        if form_encoded:
            return request.args
        else:
            return super(self.__class__, self)._format_post(request, body, encoding)

# -- RESPONSE MIXINS ----------------------------------------------------------    

class StringResponse(ResourceMixin):
    """
    Add support for writing your own response as a string
    
    Falls back to the parent class method when the response is not a string.
    """
    methods = ['_format_response']
    
    @classmethod
    def setup(cls, impl_cls):
        """
        Make the class accept basestring
        """
        impl_cls.HANDLE_TYPES = tuple(list(impl_cls.HANDLE_TYPES) + [basestring])
    
    def _format_response(self, request, response, encoding):
        """
        Allow the returning of a response that is a string
        """
        if isinstance(response, str):
            return response
        elif isinstance(response, unicode):
            return response.encode(encoding)
        else:
            return super(self.__class__, self)._format_response(request, response, encoding)
    
