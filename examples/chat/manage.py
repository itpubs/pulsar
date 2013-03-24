'''A web-based chat application, it exposes three different
:ref:`wsgi handlers <apps-wsgi-handlers>`:

* A :class:`pulsar.apps.wsgi.handlers.Router` to render the web page
* A :class:`pulsar.apps.ws.WebSocket` with the :class:`Chat` handler
* A :class:`pulsar.apps.wsgi.handlers.Router` with the :class:`Rpc` handler
  for exposing a :ref:`JSON-RPC <apps-rpc>` api.

To run the server::

    python manage.py
    
and open web browsers at http://localhost:8060

To send messages from the JSON RPC open a python shell and::

    >>> from pulsar.apps import rpc
    >>> p = rpc.JsonProxy('http://127.0.0.1:8060/rpc', force_sync=True)
    >>> p.message('Hi from rpc')
    'OK'
    
Implementation
===========================

.. autoclass:: Chat
   :members:
   :member-order: bysource
   
.. autoclass:: Rpc
   :members:
   :member-order: bysource
'''
import os
import sys
import json
from random import random
import time
try:
    import pulsar
except ImportError: #pragma nocover
    sys.path.append('../../')
    import pulsar
from pulsar.apps import ws, wsgi, rpc, pubsub

CHAT_DIR = os.path.dirname(__file__)
    

##    Web Socket Chat handler
class Chat(ws.WS):
    '''The websocket handler (:class:`pulsar.apps.ws.WS`) managing the chat
application.'''
    def on_open(self, request):
        '''When a new websocket connection is established it add connection
to the set of clients listening for messages.'''
        pubsub.add_client(request.cache['websocket'])
        
    def on_message(self, request, msg):
        '''When a new message arrives, it publishes to all listening clients.'''
        if msg:
            lines = []
            for l in msg.split('\n'):
                l = l.strip()
                if l:
                    lines.append(l)
            msg = ' '.join(lines)
            if msg:
                pubsub.publish(msg)


##    RPC MIDDLEWARE To publish messages
class Rpc(rpc.PulsarServerCommands):
    
    def rpc_message(self, request, message):
        '''Publish a message via JSON-RPC'''
        pubsub.publish(message)
        return 'OK'
    
    
class WebChat(wsgi.LazyWsgi):
    
    def __init__(self, name):
        self.name = name
        
    def setup(self):
        # Register a pubsub handler
        pubsub.register_handler(pubsub.PulsarPubSub(self.name))
        return wsgi.WsgiHandler([wsgi.Router('/', get=self.home_page),
                                 ws.WebSocket('/message', Chat()),
                                 wsgi.Router('/rpc', post=Rpc())])
        
    def home_page(self, request):
        data = open(os.path.join(CHAT_DIR, 'chat.html')).read()
        request.response.content_type = 'text/html'
        request.response.content = data % request.environ
        return request.response.start()


def server(callable=None, name=None, **kwargs):
    name = name or 'webchat'
    chat = WebChat(name)
    return wsgi.WSGIServer(name=name, callable=chat, **kwargs)


if __name__ == '__main__':  #pragma nocover
    server().start()
