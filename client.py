import asyncio
import websockets
import sys

class Client():
    def __init__(self, address, port, ssl_filename, name):
        if ssl_filename is None:
            self.ssl=False
            self.ssl_context=None
        else:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ssl_context.load_verify_locations(ssl_filename)
            self.ssl = True
            self.ssl_context = ssl_context
        self.address = address
        self.port = port
        self.name = name


    def run(self):
        while True:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(self.event_loop())
            except CancelledError as ce:
                print("Connection cancelled")
            #comment/uncomment for long form errors
            except:
                e = sys.exc_info()[0]
                print(e)
            #     print(loop.is_closed())
            # loop.run_forever()

    def get_uri(self):
        if self.ssl:
            return "wss://"+self.address+":"+self.port
        else:
            return "ws://"+self.address+":"+self.port