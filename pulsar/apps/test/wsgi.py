'''Classes for testing WSGI servers using the HttpClient'''
from functools import partial
from io import BytesIO
import logging
import socket

import pulsar
from pulsar.apps import http
from pulsar.apps.wsgi import HttpServerResponse

__all__ = ['HttpTestClient']


class DummyTransport(pulsar.Transport):
    
    def __init__(self, client, connnection):
        self.client = client
        self.connection = connnection
        
    def write(self, data):
        self.connection.data_received(data)
        
    @property
    def address(self):
        return self.connection.address
    

class DummyConnectionPool(pulsar.ConnectionPool):
    
    def get_or_create_connection(self, producer):
        client = self.connection_factory(self.address, 1, 0,
                                         producer.consumer_factory,
                                         producer)
        server = self.connection_factory(('127.0.0.1', 46387), 1, 0,
                                         producer.server_consumer,
                                         producer)
        client.connection_made(DummyTransport(producer, server))
        server.connection_made(DummyTransport(producer, client))
        return client
        
        
class HttpTestClient(http.HttpClient):
    client_version = 'Pulsar-Http-Test-Client'
    connection_pool = DummyConnectionPool

    def __init__(self, test, wsgi_handler, **kwargs):
        self.test = test
        self.wsgi_handler = wsgi_handler
        self.server_consumer = partial(HttpServerResponse, wsgi_handler)
        super(HttpTestClient, self).__init__(**kwargs)
        
    def data_received(self, connnection, data):
        pass
        
    def response(self, request):
        conn = self.get_connection(request)
        # build the protocol consumer
        consumer = conn.consumer_factory(conn)
        # start the request
        consumer.new_request(request)
        return consumer
        