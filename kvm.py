import evdev
import asyncio
import argparse
import logging
import threading
import websockets
from queue import Queue
import time

parser = argparse.ArgumentParser(description="UInput KVM")
parser.add_argument('-c', '--client', dest="client", action="store", help="Address to connect to")
parser.add_argument('-s', '--server', dest="server", action="store", help="Address to bind to")
parser.add_argument('-m', '--mouse', dest="mouse", action="store", help="Full path to mouse device")
parser.add_argument('-k', '--keyboard', dest="keyboard", action="store", help="Full path to keyboard device")
parser.add_argument('-p', '--port', dest="port", action="store", help="Port for server or client to use")
parser.add_argument('-v', '--verbose', dest="verbose", action="store_true", help="Verbose logging")

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

class Server():
    def __init__(self, mouse, keyboard):
        self.mouse = mouse
        self.keyboard = keyboard
        self.start()

    async def listen(self, websocket, path):
        print("listen")
        await websocket.recv()
        

        # async for event in self.mouse.async_read_loop():
        #     print(self.mouse.path, evdev.categorize(event), sep=': ')
            # self.out_q.put(message)
        # data = await websocket.recv()
        # self.out_q.put(data)
        # process_events(self.mouse)
        # process_events(self.keyboard)
            # await websocket.send("test")

    async def process_events(self, device):
        print("process_events")
        async for event in device.async_read_loop():
            print(device.path, evdev.categorize(event), sep=': ')

    async def run(self):
        
        self.server = websockets.serve(self.listen, "localhost", 8765)
        
        # print("---")
        # asyncio.ensure_future(self.process_events(self.mouse))
        # print("----")
        # asyncio.ensure_future(self.process_events(self.keyboard))
        # print("-----")
        
        # print("-------")

    def start(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.run())
        loop.run_forever()


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
    # server = Server(mouse, keyboard)
    # server.start()
    server_thread = threading.Thread(target=Server, args=(mouse, keyboard))
    server_thread.start()

    server_thread.join(10)






elif args.client:
    #create a uinput device for both mouse and keyboard?
    pass