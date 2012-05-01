import urllib2
import json
import sys
import os

from .auth import BasicAuth, OAuth2Auth
from .response import *
from .errors import RESTAPIError, AuthenticationNotConfigured

class RESTClient(object):
    def __init__(self, endpoint='https://api-experimental.dotcloud.com/v1', debug=False):
        self.endpoint = endpoint
        self.authenticator = None
        self.trace_id = None
        self.trace = None
        self.debug = debug

    def build_url(self, path):
        if path.startswith('/'):
            return self.endpoint + path
        else:
            return path

    def get(self, path):
        url = self.build_url(path)
        req = urllib2.Request(url)
        return self.request(req)

    def post(self, path, payload={}):
        url = self.build_url(path)
        data = json.dumps(payload)
        req = urllib2.Request(url, data, {'Content-Type': 'application/json'})
        return self.request(req)

    def put(self, path, payload={}):
        url = self.build_url(path)
        data = json.dumps(payload)
        req = urllib2.Request(url, data, {'Content-Type': 'application/json'})
        req.get_method = lambda: 'PUT'
        return self.request(req)

    def delete(self, path):
        url = self.build_url(path)
        req = urllib2.Request(url)
        req.get_method = lambda: 'DELETE'
        return self.request(req)

    def patch(self, path, payload={}):
        url = self.build_url(path)
        data = json.dumps(payload)
        req = urllib2.Request(url, data, {'Content-Type': 'application/json'})
        req.get_method = lambda: 'PATCH'
        return self.request(req)

    def request(self, req):
        if not self.authenticator:
            raise AuthenticationNotConfigured
        self.authenticator.authenticate(req)
        req.add_header('Accept', 'application/json')
        if self.trace_id:
            req.add_header('X-DotCloud-TraceID', self.trace_id)
        if self.debug:
            print >>sys.stderr, '### {method} {url} data=|{data}|'.format(
                method  = req.get_method(),
                url     = req.get_full_url(),
                data    = req.get_data()
            )
        try:
            res = urllib2.urlopen(req)
            if res and self.debug:
                print >>sys.stderr, '### {code}'.format(code=res.code)
            self.trace_id = res.headers.get('X-DotCloud-TraceID')
            if self.trace:
                self.trace(self.trace_id)
            return self.make_response(res)
        except urllib2.HTTPError, e:
            if e.code == 401 and self.authenticator.retriable:
                if self.authenticator.prepare_retry():
                    return self.request(req)
            return self.make_response(e)

    def make_response(self, res):
        if res.headers['Content-Type'] == 'application/json':
            data = json.loads(res.read())
        elif res.code == 204:
            return None
        else:
            raise RESTAPIError(code=500,
                               desc='Unsupported Media type: {0}'.format(res.headers['Content-Type']))
        if res.code >= 400:
            raise RESTAPIError(code=res.code, desc=data['error']['description'])
        return BaseResponse.create(res=res, data=data)
