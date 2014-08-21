

class SessionStorage(object):

    """Requires at least Requests==2.1.0 to work correctly"""

    def __init__(self, session):
        session.hooks['response'].append(self.hook)
        self.requests = []

    def hook(self, response, **kwargs):
        request = response.request
        data = {
            'request': {
                'method': request.method,
                'url': request.url,
                'headers': request.headers.items(),
                'body': request.body,
            },
            'response': {
                'status_code': response.status_code,
                'headers': response.headers.items(),
                'body': response.content,
            }
        }
        self.requests.append(data)

    def get_requests(self):
        return self.requests
