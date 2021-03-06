import cgi
import itertools
from io import StringIO
import utils
import time


class RemoveTrailingSlashesMiddleware(object):
    '''Middleware to strip and redirect any links with trailing slashes'''
    def __init__(self, app):
        self.app = app

    def __call__(self, e, h):
        url = e['PATH_INFO']
        if url != '/' and url.endswith('/'):
            h('303 See Other', [('Location', url.rstrip('/'))])
            return []

        return self.app(e, h)


class JSONPCallbackMiddleware(object):
    '''Adds JSONP support for ajax calls'''
    def __init__(self, app):
        self.app = app
        self.callback_query_parameters = ['jsonp', 'callback']
        self.javascript_mime_types = \
        ['text/javascript', 'application/javascript', 'application/ecmascript',
         'application/x-ecmascript']

    def __call__(self, environ, start_response):
        if not 'HTTP_X_REQUESTED_WITH' in environ or \
           'XMLHttpRequest' != environ['HTTP_X_REQUESTED_WITH']:
            return self.app(environ, start_response)

        if not 'QUERY_STRING' in environ:
            return self.app(environ, start_response)

        if not any(p in environ['QUERY_STRING'] \
           for p in self.callback_query_parameters):
            return self.app(environ, start_response)

        if not 'HTTP_ACCEPT' in environ:
            return self.app(environ, start_response)

        if not any(m in environ['HTTP_ACCEPT']
           for m in self.javascript_mime_types):
            return self.app(environ, start_response)
            
        buffer = StringIO()

        def custom_start_response(status, headers, exc_info=None):
            return buffer

        result = list(self.app(environ, custom_start_response))

        query_string = cgi.parse_qs(environ['QUERY_STRING'].lstrip('?'))
        callback_key = 'callback' if 'callback' in query_string else 'jsonp'
        callback_name = query_string[callback_key]

        start = callback_name[0] + '('
        length = len(start) + len(result[0]) + 1
        start_response('200 OK', [('Content-Length', str(length))])
        return itertools.chain.from_iterable([[start], result, [')']])

        
class NoCacheMiddleware(object):
    '''Adds a no caching header to the response'''
    CONTROL_VALUE = 'max-age=0,no-cache,no-store,post-check=0,pre-check=0'
    
    def __init__(self, app):
        self.app = app
        self.expires_value = time.strftime("%a, %d %b %Y %H:%M:%S UTC", utils.utcnow())

    def __call__(self, environ, start_response):
        def custom_start_response(status, headers, exc_info=None):
            headers += [('Cache-Control', NoCacheMiddleware.CONTROL_VALUE),
                        ('Expires', self.expires_value)]
            return start_response(status, headers, exc_info);

        return self.app(environ, custom_start_response)