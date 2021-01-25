import evdev
import asyncio
import argparse
import logging
import threading
import websockets
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
from asyncio.exceptions import CancelledError
from queue import Queue
import time
import json
import sys
import ssl

parser = argparse.ArgumentParser(description="UInput KVM")
parser.add_argument('-c', '--client', dest="client", action="store", help="Address to connect to")
parser.add_argument('-n', '--name', dest="name", action="store", help="Client Name")
parser.add_argument('-s', '--server', dest="server", action="store", help="Address to bind to")
parser.add_argument('-m', '--mouse', dest="mouse", action="store", help="Full path to mouse device")
parser.add_argument('-k', '--keyboard', dest="keyboard", action="store", help="Full path to keyboard device")
parser.add_argument('-d', '--dev_name', dest="dev_name", default="UInput KVM", action="store", help="Name of device to be created for remote interactions")
parser.add_argument('-p', '--port', dest="port", action="store", default="8765", help="Port for server or client to use. Defaults to 8765")
parser.add_argument('-v', '--verbose', dest="verbose", action="store_true", help="Verbose logging")
parser.add_argument('-g', '--grab', dest="grab", action="store_true", help="Grab all input from devices")
parser.add_argument('-ls', '--list', dest="list", action="store_true", help="List device available on computer")
#TODO add config file reading that maps connecting ip addresses to client names
# parser.add_argument('--config', dest="config", action="store", help="Config file for hotkey bindings")
#TODO fix ssl support? Does not work as expected!
parser.add_argument('--ssl', dest="ssl", default=False, action="store", help="Self signed key file for ssl. (.pem) (also not working for me)")

args = parser.parse_args()

# logging.basicConfig(format='%(asctime)s %(message)s')
# log = logging.getLogger("kvm")

# if args.verbose:
#     log.setLevel(logging.DEBUG)
# else:
#     log.setLevel(logging.INFO)

# ch = logging.StreamHandler()
# ch.setLevel(logging.DEBUG)

# formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
# ch.setFormatter(formatter)
# log.addHandler(ch)

#start a server that just passes around messages and keeps track of the clients
class Server():
    def __init__(self, address, port, ssl_filename):
        if ssl_filename is None:
            self.ssl_context = None
        else:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ssl_context.load_verify_locations(ssl_filename)
            self.ssl_context = ssl_context
        self.address = address
        self.port = port
        self.clients = set()
        self.devices = set()
        self.run()

    async def connect(self, ws):
        if self.address == ws.remote_address[0]:
            print("Device added: ", ws.remote_address[0])
            self.devices.add(ws)
        else:
            print("Client added: ", ws.remote_address[0])
            self.clients.add(ws)

    async def disconnect(self, ws):
        if self.address == ws.remote_address[0]:
            print("Device lost: ", ws.remote_address[0])
            self.devices.remove(ws)
        else:
            print("Client lost: ", ws.remote_address[0])
            self.clients.remove(ws)

    async def broadcast(self, message):
        if self.clients:
            print(self.clients)
            await asyncio.wait([client.send(message) for client in self.clients])

    async def listen(self, websocket, path):
        await self.connect(websocket)
        try:
            async for message in websocket:
                print(message)
                try:
                    data = json.loads(message)
                    print(data)
                except:
                    print("json error")
                await self.broadcast(message)
        except ConnectionClosedError as cce:
            print("Connection Lost")
            print(cce)
            await self.disconnect(websocket)
        except ConnectionClosedOK as cco:
            print("Connection closed")
        finally:
            pass

    def run(self):
        print("Starting server")
        loop = asyncio.new_event_loop()
        self.server = websockets.serve(self.listen, self.address, int(self.port), ssl=self.ssl_context, loop=loop)
        loop.run_until_complete(self.server)
        loop.run_forever()
        

class Client():
    def run(self):
        while True:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(self.event_loop())
            except CancelledError as ce:
                print("Connection cancelled")
            # except:
            #     e = sys.exc_info()[0]
            #     print(e)
            #     print(loop.is_closed())
            # loop.run_forever()

    def get_uri(self):
        if self.ssl:
            return "wss://"+self.address+":"+self.port
        else:
            return "ws://"+self.address+":"+self.port

#HOST that sends out input events
class HostClient(Client):
    def __init__(self, address, port, ssl_filename, device):
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
        self.device = device
        self.run()

    async def event_loop(self):
        uri = self.get_uri()
        async with websockets.connect(uri, ssl=self.ssl_context) as websocket:
            # await websocket.send(json.dumps({"name":"device"}))
            async for ev in self.device.async_read_loop():
                #TODO add configable hotkeys that will swap computers info is sent to
                data = {
                    "timestamp": str(ev.timestamp()),
                    "type": ev.type,
                    "code": ev.code,
                    "value": ev.value
                }
                try:
                    await websocket.send(json.dumps(data))
                except ConnectionClosedOK as cco:
                    print("Connection Closed!")
                # except ConnectionClosedError as cce:
                #     print("Connection error")

#client that recieves input events and executes them via uinput!
class RemoteClient(Client):
    def __init__(self, address, port, ssl, dev_name):
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
        self.ui = evdev.UInput(name=dev_name)
        self.run()

    async def event_loop(self):
        uri = self.get_uri()
        print("Connecting to: ", uri)
        async with websockets.connect(uri, ssl=self.ssl_context) as websocket:
            async for msg in websocket:
                data = json.loads(msg)
                print(time.time()-float(data['timestamp']), data)
                self.ui.write(data["type"], data["code"], data["value"])


def get_devices():
    return [evdev.InputDevice(path) for path in evdev.list_devices()]

def grab_device(devices, path):
    return_device = None
    for device in devices:
        if path==device.path:
            device.close()
            return_device = evdev.InputDevice(device.path)
        else:
            device.close()

    return return_device

print("Getting list of devices")
devices = get_devices()
if args.list:
    for dev in get_devices():
        print(dev.path, dev.name, dev.phys)
    sys.exit()

if args.server:
    #create server
    print("Making server thread")
    server_thread = threading.Thread(target=Server, args=(args.server, args.port, args.ssl))
    server_thread.name = "Server Thread"
    print("Starting server thread")
    server_thread.start()
    time.sleep(1)

    #grab mouse
    if args.mouse:
        mouse = grab_device(devices, args.mouse)
        if args.grab:
            mouse.grab()
        print("Making MouseHostClient thread")
        mouse_host_thread = threading.Thread(target=HostClient, args=(args.server, args.port, args.ssl, mouse))
        mouse_host_thread.name = "Mouse Client Thread"
        print("Starting mousehostclient thread")
        mouse_host_thread.start()
        
    #grab keyboard
    if args.keyboard:
        keyboard = grab_device(devices, args.keyboard)
        if args.grab:
            keyboard.grab()
        print("Making KeyboardHostClient thread")
        keyboard_host_thread = threading.Thread(target=HostClient, args=(args.server, args.port, args.ssl, keyboard))
        keyboard_host_thread.name = "Keyboard Client Thread"
        print("Starting keyboardhostclient thread")
        keyboard_host_thread.start()
        
elif args.client:
    #create a uinput device for both mouse and keyboard?
    print("Making RemoteClient thread")
    remote_thread = threading.Thread(target=RemoteClient, args=(args.client, args.port, args.ssl, args.dev_name))
    remote_thread.name = "Remote Thread"
    print("Starting RemoteClient thread")
    remote_thread.start()
    pass