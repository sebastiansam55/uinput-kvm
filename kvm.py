import evdev
import asyncio
import argparse
import logging
import threading
import websockets
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
from queue import Queue
import time
import json
# import sys

parser = argparse.ArgumentParser(description="UInput KVM")
parser.add_argument('-c', '--client', dest="client", action="store", help="Address to connect to")
parser.add_argument('-n', '--name', dest="name", action="store", help="Client Name")
parser.add_argument('-s', '--server', dest="server", action="store", help="Address to bind to")
parser.add_argument('-m', '--mouse', dest="mouse", action="store", help="Full path to mouse device")
parser.add_argument('-k', '--keyboard', dest="keyboard", action="store", help="Full path to keyboard device")
parser.add_argument('-d', '--dev_name', dest="dev_name", default="UInput KVM", action="store", help="Name of device to be created for remote interactions")
parser.add_argument('-p', '--port', dest="port", action="store", default="8765", help="Port for server or client to use")
parser.add_argument('-v', '--verbose', dest="verbose", action="store_true", help="Verbose logging")
#TODO rip list function from uinput keyboard mapper

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
    def __init__(self, address, port):
        self.address = address
        self.port = port
        self.clients = set()
        self.run()

    async def connect(self, ws):
        self.clients.add(ws)

    async def disconnect(self, ws):
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
        self.server = websockets.serve(self.listen, self.address, int(self.port), loop=loop)
        loop.run_until_complete(self.server)
        loop.run_forever()
        

class Client():
    def run(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.event_loop())
        loop.run_forever()

    def get_uri(self):
        return "ws://"+self.address+":"+self.port

#HOST that sends out input events
class HostClient(Client):
    def __init__(self, address, port, mouse, keyboard):
        self.address = address
        self.port = port
        self.mouse = mouse
        self.keyboard = keyboard
        self.run()

    async def event_loop(self):
        uri = self.get_uri()
        async with websockets.connect(uri) as websocket:
            async for ev in self.mouse.async_read_loop():
                #TODO add configable hotkeys that will swap computers
                data = {
                    "type": ev.type,
                    "code": ev.code,
                    "value": ev.value
                }
                try:
                    await websocket.send(json.dumps(data))
                except ConnectionClosedOK as cco:
                    print("Connection Closed!")
            

#client that recieves input events and executes them via uinput!
class RemoteClient(Client):
    def __init__(self, address, port, dev_name):
        self.address = address
        self.port = port
        self.ui = evdev.UInput(name=dev_name)
        self.run()

    async def event_loop(self):
        uri = self.get_uri()
        async with websockets.connect(uri) as websocket:
            async for msg in websocket:
                data = json.loads(msg)
                print(data)
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

if args.server:
    #grab mouse
    if args.mouse:
        mouse = grab_device(devices, args.mouse)
        
    #grab keyboard
    if args.keyboard:
        keyboard = grab_device(devices, args.keyboard)
        
    #create server
    print("Making server thread")
    server_thread = threading.Thread(target=Server, args=(args.server, args.port))
    print("Starting server thread")
    server_thread.start()
    time.sleep(1)

    print("Making HostClient thread")
    host_thread = threading.Thread(target=HostClient, args=(args.server, args.port, mouse,keyboard))
    print("Starting hostclient thread")
    host_thread.start()

elif args.client:
    #create a uinput device for both mouse and keyboard?
    print("Making RemoteClient thread")
    remote_thread = threading.Thread(target=RemoteClient, args=(args.client, args.port, args.dev_name))
    print("Starting RemoteClient thread")
    remote_thread.start()
    pass