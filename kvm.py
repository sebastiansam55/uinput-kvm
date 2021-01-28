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
parser.add_argument('-v', '--verbose', dest="verbose", action="store_true", help="Verbose logging (Does nothing rn)")
#TODO work out system that allows for non-exclusive grabs
parser.add_argument('-g', '--grab', dest="grab", action="store_true", help="Grab all input from devices")
parser.add_argument('-ls', '--list', dest="list", action="store_true", help="List device available on computer")
parser.add_argument('--config', dest="config", action="store", help="Config file for hotkey bindings")
#TODO fix ssl support? Does not work as expected!
parser.add_argument('--ssl', dest="ssl", action="store", help="Self signed key file for ssl. (.pem) (also not working for me)")
parser.add_argument('--debug', dest="debug", default=False, action="store_true", help="Enable client debug (will not write events)")
parser.add_argument('--default', dest="default", action="store", default=None, help="Default client to send events to")
parser.add_argument('-b', '--broadcast', action="store_true", default=False, help="Broadcast to all clients")


args = parser.parse_args()

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
if args.verbose:
    handler.setLevel(logging.DEBUG)
else:
    handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(message)s')
handler.setFormatter(formatter)
log.addHandler(handler)

#start a server that just passes around messages and keeps track of the clients
class Server():
    def __init__(self, address, port, ssl_filename, name, default, config):
        if ssl_filename is None:
            ssl_context = None
        else:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ssl_context.load_verify_locations(ssl_filename)
        self.clients = []
        self.config = config
        self.sendto = default
        self.ipmap = {}
        self.run(address, port, ssl_context)

    async def connect(self, ws):
        log.info("Client added: "+ws.remote_address[0])
        self.clients.append(ws)

    async def disconnect(self, ws):
        log.info("Client lost: "+ws.remote_address[0])
        self.clients.remove(ws)

    async def broadcast(self, message):
        if self.clients:
            log.debug(self.clients)
            remove = False
            rm_list = []
            for client in self.clients:
                try:
                    log.debug("Send to: "+client.remote_address[0])
                    await (client.send(message))
                except ConnectionClosedOK:
                    remove = True
                    rm_list.append(client)
            if remove:
                for client in rm_list:
                    log.debug("Remove: "+client.remote_address)
                    self.clients.remove(client)

    async def sendto_name(self, message):
        #takes a name and checks the config
        ip = self.ipmap.get(self.sendto)
        if ip: #if we can get an ip from the current sendto name
            for client in self.clients:
                if client.remote_address[0] == ip:
                    await client.send(json.dumps(message))

    async def process_message(self, message, ip):
        try:
            data = json.loads(message.replace("'", "\""))
            log.debug(data)
        except:
            log.error("JSON formatting error in process message")

        if data.get("change_sendto"):
            log.debug("Changing sendto from "+self.sendto+" to "+data.get("change_sendto"))
            self.sendto = data.get("change_sendto")
        elif data.get("ident"):
            # clients send this when they first connect.
            # Associate with IP it was sent from for lookup
            self.ipmap[data.get("ident")] = ip
        else:
            # print(time.time()-float(data.get('timestamp')), data)
            data["sendto"] = self.sendto
            if args.broadcast:
                await self.broadcast(json.dumps(data))
            else:
                await self.sendto_name(data)


    async def listen(self, ws, path):
        await self.connect(ws)
        try:
            async for message in ws:
                asyncio.create_task(self.process_message(message, ws.remote_address[0]))
        except ConnectionClosedError as cce:
            log.info("Connection Lost")
            traceback.print_exc()
            await self.disconnect(ws)
        except ConnectionClosedOK as cco:
            log.info("Connection closed")
            traceback.print_exc()


    def run(self, address, port, ssl_context):
        log.info("Starting server")
        loop = asyncio.new_event_loop()
        self.server = websockets.serve(self.listen, address, int(port), ssl=ssl_context, loop=loop)
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
                log.info("Attempting grab: "+self.device_desc)
                self.device = grab_device(devices, self.device_desc)
                if self.device:
                    log.info("Device captured: "+self.device_desc)
                    try:
                        await self.dev_event_loop(sendto, websocket)
                    except OSError:
                        log.error("device disconnected?")
                #wait 5 seconds before trying to grab
                await asyncio.sleep(5)


    async def change_sendto(self, websocket, sendto):
        log.info("Sending to: ", sendto)
        data = {"change_sendto": sendto}
        try:
            await websocket.send(json.dumps(data))
        except ConnectionClosedOK as cco:
            log.error("Connection closed")

class KeyboardClient(HostClient):
    def reset_keys(self, held_keys, problem_keys):
            key_list = keyboard.active_keys()
            log.debug("Active keys: "+str(key_list))
            for key in key_list:
                keyboard.write(e.EV_KEY, key, 0)
                held_keys.remove(key)
            key_list = keyboard.active_keys()
            log.debug("Active keys: "+str(key_list))
            for key in problem_keys:
                keyboard.write(e.EV_KEY, key, 1)
                keyboard.write(e.EV_KEY, key, 0)
            # keyboard.syn()
            # for key in reset_list:



    async def dev_event_loop(self, sendto, websocket):
        modifiers = self.config.get("modifiers")
        held_keys = []
        async for ev in self.device.async_read_loop():
            if ev.value == 1: #modifier pressed down
                held_keys.append(ev.code)
            elif ev.value == 0: #modifier released!
                if ev.code in held_keys:
                    held_keys.remove(ev.code)

            log.debug(held_keys)

            all_held = True
            for key in modifiers:
                if key in held_keys:
                    all_held = True
                else:
                    all_held = False
                    break

            if all_held:
                log.info("Key event detected when left [shift alt ctrl] held"+str(ev.code))
                for client in self.hotkeys:
                    if client[1] == ev.code:
                        #code to reset keys and grab/ungrab keyboard/mouse
                        if client[0] == self.name:
                            try:
                                self.reset_keys(held_keys, modifiers)
                                log.debug(held_keys)
                                keyboard.ungrab()
                            except:
                                log.debug("Tried ungrab on already ungrabbed dev")
                            try:
                                mouse.ungrab()
                            except:
                                log.debug("Tried ungrab on already ungrabbed dev")
                            await self.change_sendto(websocket, None)
                        else:
                            try:
                                self.reset_keys(held_keys, modifiers)
                                log.debug(held_keys)
                                keyboard.grab()
                            except:
                                log.debug("Tried ungrab on already ungrabbed dev")
                            try:
                                mouse.grab()
                            except:
                                log.debug("Tried ungrab on already ungrabbed dev")
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
                log.error("Connection Closed!")

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
                log.error("Connection Closed!")

def get_devices():
    return [evdev.InputDevice(path) for path in evdev.list_devices()]

def grab_device(devices, descriptor):
    #determine if descriptor is a path or a name
    return_device = None
    if len(descriptor) <= 2: #assume that people don't have more than 99 input devices
        descriptor = "/dev/input/event"+descriptor
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
        print("Path:","\""+dev.path+"\"", "Name: \""+dev.name+"\"", dev.phys)
    sys.exit()

if args.config:
    log.info("Loading list of clients")
    with open(args.config, 'r') as f:
        config_data = json.load(f)
        log.debug(config_data)
else:
    config_data = None

if args.server:
    #create server
    log.info("Making server thread")
    server_thread = threading.Thread(target=Server, args=(args.server, args.port, args.ssl, args.name, args.default, config_data))
    server_thread.name = "Server Thread"
    log.info("Starting server thread")
    server_thread.start()
    time.sleep(1)

    #grab mouse
    if args.mouse:
        log.info("Making MouseHostClient thread")
        mouse_host_thread = threading.Thread(target=MouseClient, args=(args.server, args.port, args.ssl, args.name, args.mouse, config_data))
        mouse_host_thread.name = "Mouse Client Thread"
        log.info("Starting mousehostclient thread")
        mouse_host_thread.start()
        
    #grab keyboard
    if args.keyboard:
        log.info("Making KeyboardHostClient thread")
        keyboard_host_thread = threading.Thread(target=KeyboardClient, args=(args.server, args.port, args.ssl, args.name, args.keyboard, config_data))
        keyboard_host_thread.name = "Keyboard Client Thread"
        log.info("Starting keyboardhostclient thread")
        keyboard_host_thread.start()

    #grab stadia controller
    if args.controller:
        log.info("Making ControllerClient thread")
        stadia_host_thread = threading.Thread(target=MouseClient, args=(args.server, args.port, args.ssl, args.name, args.controller, config_data))
        stadia_host_thread.name = "Controller Client Thread"
        log.info("Starting Controller thread")
        stadia_host_thread.start()
        
elif args.client:
    #create a uinput device for both mouse and keyboard?
    log.info("Making Linux thread")
    remote_thread = threading.Thread(target=LinuxClient, args=(args.client, args.port, args.ssl, args.name, args.dev_name, None, args.debug))
    remote_thread.name = "Linux Client Thread"
    log.info("Starting LinuxClient thread")
    remote_thread.start()