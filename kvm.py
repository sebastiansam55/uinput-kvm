import evdev
import asyncio
import websockets
import argparse
import logging
import threading
from queue import Queue

from server import Server

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

def process_events(device, in_q, out_q):
    for event in device.async_read_loop():
        in_q.put(event)
        server_thread.join()
        # print(device.path, evdev.categorize(event), sep=': ')


print("Getting list of devices")
devices = get_devices()

if args.server:
    #create the server
    # s = Server()
    input_queue = Queue() #input from local computer
    output_queue = Queue() #output from remote
    server_thread = Server(input_queue, output_queue)
    server_thread.start()




    #grab mouse
    if args.mouse:
        mouse = grab_device(devices, args.mouse)
        
    #grab keyboard
    if args.keyboard:
        keyboard = grab_device(devices, args.keyboard)
        
    mouse_event_thread = threading.Thread(target=process_events, args=(mouse, input_queue, output_queue))
    mouse_event_thread.start()
    keyboard_event_thread = threading.Thread(target=process_events, args=(keyboard,input_queue, output_queue))
    keyboard_event_thread.start()



elif args.client:
    #create a uinput device for both mouse and keyboard?
    pass