import evdev
from evdev import AbsInfo, ecodes as e
import asyncio
import argparse
import logging
import threading
import websockets
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
from asyncio import CancelledError
import time
import json
import sys
import os
import traceback
import ssl

from client import Client
from linux_client import LinuxClient

parser = argparse.ArgumentParser(description="UInput KVM")
parser.add_argument('-c', '--client', dest="client", action="store", help="Address to connect to")
parser.add_argument('-n', '--name', dest="name", default=os.uname()[1], action="store", help="Client Name")
parser.add_argument('-s', '--server', dest="server", action="store", help="Address to bind to")
#TODO grab via a different method
parser.add_argument('-m', '--mouse', dest="mouse", action="store", help="Full path to mouse/any other device device")
parser.add_argument('-k', '--keyboard', dest="keyboard", action="store", help="Full path to keyboard device. Must be a keyboard device")
parser.add_argument('--controller', dest='controller', action="store", help="Full path to the controller device") #used if you want to send a keyboard, mouse and controller. Otherwise you can use the -m flag
parser.add_argument('-d', '--dev_name', dest="dev_name", default="UInput KVM", action="store", help="Name of device to be created for remote interactions")
parser.add_argument('-p', '--port', dest="port", action="store", default="8765", help="Port for server or client to use. Defaults to 8765")
parser.add_argument('-v', '--verbose', dest="verbose", action="store_true", help="Verbose logging")
#TODO work out system that allows for non-exclusive grabs
parser.add_argument('-g', '--grab', dest="grab", action="store_true", help="Grab all input from devices")
parser.add_argument('-ls', '--list', dest="list", action="store_true", help="List device available on computer")
parser.add_argument('--config', dest="config", action="store", help="Config file for hotkey bindings")
#TODO fix ssl support? Does not work as expected!
parser.add_argument('--ssl', dest="ssl", action="store", help="Self signed key file for ssl. (.pem) (also not working for me)")
parser.add_argument('--debug', dest="debug", default=False, action="store_true", help="Enable client debug (will not write events)")
parser.add_argument('--default', dest="default", action="store", default=None, help="Default client to send events to")


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
    def __init__(self, address, port, ssl_filename, name, default, config):
        if ssl_filename is None:
            self.ssl_context = None
        else:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ssl_context.load_verify_locations(ssl_filename)
            self.ssl_context = ssl_context
        self.address = address
        self.port = port
        self.clients = set()
        self.config = config
        self.sendto = default
        self.ipmap = {}
        self.run()

    async def connect(self, ws):
        print("Client added: ", ws.remote_address[0])
        self.clients.add(ws)

    async def disconnect(self, ws):
        print("Client lost: ", ws.remote_address[0])
        self.clients.remove(ws)

    async def broadcast(self, message):
        if self.clients:
            print(self.clients)
            remove = False
            rm_list = []
            for client in self.clients:
                pass
                try:
                    await (client.send(message))
                except ConnectionClosedOK:
                    remove = True
                    rm_list.append(client)
            if remove:
                for client in rm_list:
                    self.clients.remove(client)


    async def sendto_name(self, message, recp):
        #takes a name an checks the config
        if self.config.get(recp):
            print(self.config.get(recp))
                            

    async def listen(self, websocket, path):
        await self.connect(websocket)
        try:
            async for message in websocket:
                # print(message)
                try:
                    data = json.loads(message)
                    print(data)
                except:
                    print("json error")
                if data.get("change_sendto"):
                    print("Changing sendto from", self.sendto, "to", data.get("change_sendto"))
                    self.sendto = data.get("change_sendto")
                elif data.get("ident") is None:
                    # print(data.get("sendto"))
                    data["sendto"] = self.sendto
                    await self.broadcast(json.dumps(data))
                        # await self.sendto_name(message, data.get("sendto"))
                    # await self.broadcast(message)

                else:
                    pass
        except ConnectionClosedError as cce:
            print("Connection Lost")
            traceback.print_exc()
            await self.disconnect(websocket)
        except ConnectionClosedOK as cco:
            print("Connection closed")
            traceback.print_exc()


    def run(self):
        print("Starting server")
        loop = asyncio.new_event_loop()
        self.server = websockets.serve(self.listen, self.address, int(self.port), ssl=self.ssl_context, loop=loop)
        loop.run_until_complete(self.server)
        loop.run_forever()
        

#HOST that sends out input events
class HostClient(Client):
    def __init__(self, address, port, ssl_filename, name, device_desc, config_data):
        super().__init__(address, port, ssl_filename, name)
        self.config = config_data
        self.hotkeys = self.config.get("hotkeys")
        self.device = None
        self.device_desc = device_desc
        self.run()

    async def event_loop(self):
        uri = self.get_uri()
        sendto = None
        async with websockets.connect(uri, ssl=self.ssl_context) as websocket:
            await websocket.send(json.dumps({"ident":self.name}))
            while True:
                #add code from uinput-keyboardsremapper to loop try and grab device
                devices = get_devices()
                print("Attempting grab: ", self.device_desc)
                self.device = grab_device(devices, self.device_desc)
                if self.device:
                    print("Device captured: ", self.device_desc)
                    try:
                        await self.dev_event_loop(sendto, websocket)
                    except OSError:
                        print("device disconnected?")
                #wait 5 seconds before trying to grab
                await asyncio.sleep(5)


    async def change_sendto(self, websocket, sendto):
        print("Sending to: ", sendto)
        data = {"change_sendto": sendto}
        try:
            await websocket.send(json.dumps(data))
        except ConnectionClosedOK as cco:
            print("Connection closed")

class KeyboardClient(HostClient):
    def reset_keys(self, held_keys, problem_keys):
            key_list = keyboard.active_keys()
            print("Active keys: ",key_list)
            for key in key_list:
                keyboard.write(e.EV_KEY, key, 0)
                held_keys.remove(key)
            key_list = keyboard.active_keys()
            print("Active keys: ",key_list)
            for key in problem_keys:
                keyboard.write(e.EV_KEY, key, 1)
                keyboard.write(e.EV_KEY, key, 0)
            # keyboard.syn()
            # for key in reset_list:



    async def dev_event_loop(self, sendto, websocket):
        modifiers = self.config.get("modifiers")
        # print(modifiers)
        held_keys = []
        async for ev in self.device.async_read_loop():
            if ev.value == 1: #modifier pressed down
                held_keys.append(ev.code)
            elif ev.value == 0: #modifier released!
                if ev.code in held_keys:
                    held_keys.remove(ev.code)

            print(held_keys)

            all_held = True
            for key in modifiers:
                if key in held_keys:
                    all_held = True
                else:
                    all_held = False
                    break

            if all_held:
                print("Key event detected when left [shift alt ctrl] held", ev)
                for client in self.hotkeys:
                    if client[1] == ev.code:
                        #code to reset keys and grab/ungrab keyboard/mouse
                        if client[0] == self.name:
                            try:
                                self.reset_keys(held_keys, modifiers)
                                print(held_keys)
                                keyboard.ungrab()
                            except:
                                print("Tried ungrab on already ungrabbed dev")
                            try:
                                mouse.ungrab()
                            except:
                                print("Tried ungrab on already ungrabbed dev")
                            await self.change_sendto(websocket, None)
                        else:
                            try:
                                self.reset_keys(held_keys, modifiers)
                                print(held_keys)
                                keyboard.grab()
                            except:
                                print("Tried ungrab on already ungrabbed dev")
                            try:
                                mouse.grab()
                            except:
                                print("Tried ungrab on already ungrabbed dev")
                            sendto = client[0]
                            await self.change_sendto(websocket, sendto)


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

#says mouse but will send any captured events.
class MouseClient(HostClient):
    #mouse is much simpler
    async def dev_event_loop(self, sendto, websocket):
        async for ev in self.device.async_read_loop():
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

def get_devices():
    return [evdev.InputDevice(path) for path in evdev.list_devices()]

def grab_device(devices, descriptor):
    #determine if descriptor is a path or a name
    return_device = None
    if "/dev/" in descriptor: #assume function was passed a path
        for device in devices:
            if descriptor==device.path:
                device.close()
                return_device = evdev.InputDevice(device.path)
            else:
                device.close()
    else: #assume that function was passed a plain text name
        for device in devices:
            if descriptor==device.name:
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

if args.config:
    print("Loading list of clients")
    with open(args.config, 'r') as f:
        config_data = json.load(f)
        print(config_data)
else:
    config_data = None

if args.server:
    #create server
    print("Making server thread")
    server_thread = threading.Thread(target=Server, args=(args.server, args.port, args.ssl, args.name, args.default, config_data))
    server_thread.name = "Server Thread"
    print("Starting server thread")
    server_thread.start()
    time.sleep(1)

    #grab mouse
    if args.mouse:
        print("Making MouseHostClient thread")
        mouse_host_thread = threading.Thread(target=MouseClient, args=(args.server, args.port, args.ssl, args.name, args.mouse, config_data))
        mouse_host_thread.name = "Mouse Client Thread"
        print("Starting mousehostclient thread")
        mouse_host_thread.start()
        
    #grab keyboard
    if args.keyboard:
        print("Making KeyboardHostClient thread")
        keyboard_host_thread = threading.Thread(target=KeyboardClient, args=(args.server, args.port, args.ssl, args.name, args.keyboard, config_data))
        keyboard_host_thread.name = "Keyboard Client Thread"
        print("Starting keyboardhostclient thread")
        keyboard_host_thread.start()

    #grab stadia controller
    if args.controller:
        print("Making ControllerClient thread")
        stadia_host_thread = threading.Thread(target=MouseClient, args=(args.server, args.port, args.ssl, args.name, args.controller, config_data))
        stadia_host_thread.name = "Controller Client Thread"
        print("Starting Controller thread")
        stadia_host_thread.start()
        
elif args.client:
    #create a uinput device for both mouse and keyboard?
    print("Making Linux thread")
    remote_thread = threading.Thread(target=LinuxClient, args=(args.client, args.port, args.ssl, args.name, args.dev_name, None, args.debug))
    remote_thread.name = "Linux Client Thread"
    print("Starting LinuxClient thread")
    remote_thread.start()