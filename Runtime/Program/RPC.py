from xmlrpc.server import SimpleXMLRPCServer as RPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler as RPCHandle
from socketserver import ThreadingMixIn
from xmlrpc.client import ServerProxy as RPCClient_ServerProxy
from socket import setdefaulttimeout as socket_setdefaulttimeout

def Timeout(Value=None):
    socket_setdefaulttimeout(Value)

class RPCSilentHandle(RPCHandle):
    def log_message(self, format, *args):
        pass

    def log_error(self, format, *args):
        pass

def Client(Port, IP='127.0.0.1'):
    return RPCClient_ServerProxy('http://'+IP+':'+str(Port))

class Server(ThreadingMixIn, RPCServer):
    def __init__(self, Port, IP=''):
        super().__init__((IP, Port), requestHandler=RPCSilentHandle, allow_none=True)
        self.register_introspection_functions()

    def __str__(self):
        return f"RpcServer[IP={self.server_address[0]}, Port={self.server_address[1]}]"

    def __repr__(self):
        return f"RpcServer[IP={self.server_address[0]}, Port={self.server_address[1]}]"

    def Start(self):
        self.serve_forever()

    def Close(self):
        self.shutdown()

    def Method(self, Function, Trigger=None):
        self.register_function(Function, Trigger)