from websocket import create_connection
import evdev
import argparse
import os
import time
import sys

parser = argparse.ArgumentParser(description="RPi0 optimized UInput forwarding")
parser.add_argument('-c', '--client', dest="client", action="store", help="Address to connect to")
parser.add_argument('-n', '--name', dest="name", default=os.uname()[1], action="store", help="Client Name")
parser.add_argument('-d', '--device_desc', dest="device_desc", action="store", help="Name of device to grab")
parser.add_argument('-p', '--port', dest="port", action="store", default="8765", help="Port for server or client to use. Defaults to 8765")
parser.add_argument('-v', '--verbose', dest="verbose", action="store_true", help="Verbose logging")
parser.add_argument('--ssl', dest="ssl", action="store", help="Self signed key file for ssl. (.pem) (also not working for me)")
parser.add_argument('--debug', dest="debug", default=False, action="store_true", help="Enable client debug (will not write events)")
parser.add_argument('--default', dest="default", action="store", default="null", help="Default client to send events to")

args = parser.parse_args()


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

def get_dev():
    devices = get_devices()
    print("Attempting grab: ", args.device_desc)
    device = grab_device(devices, args.device_desc)
    if device:
        print("Device captured: ", args.device_desc)
        return device

def connect():
    ws = None
    try:
        ws = create_connection("ws://"+args.client+":"+args.port)
        ws.send(str({"ident":args.name}))
    except:
        print("Connection Error")
    return ws


ws = None
while ws is None:
    ws = connect()
    time.sleep(1)
device = get_dev()

while True:
    try:
        for ev in device.read_loop():
            ts = ev.timestamp()
            if time.time()>ts+1: #forget events over 1s old
                continue
            data = {
                "timestamp": str(ts),
                "type": ev.type,
                "code": ev.code,
                "value": ev.value,
                "sendto": args.default
            }
            try:
                ret = ws.send(str(data))
            except BrokenPipeError:
                ws = None
                while ws is None:
                    ws = connect()
                    time.sleep(1)
                print(ret)
    except OSError:
        print("Device error, or device disconnect")
        device = None
        while device is None:
            device = get_dev()
            time.sleep(1)
