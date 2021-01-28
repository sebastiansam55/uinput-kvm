import json
from evdev import AbsInfo, ecodes as e
import evdev
import argparse
import os
import websockets
import time

from client import Client

#client that recieves input events and executes them via uinput!
class LinuxClient(Client):
    def __init__(self, address, port, ssl_filename, name, dev_name, config_data=None, debug=False, dd=None, exec_all=False):
        super().__init__(address, port, ssl_filename, name)
        self.config = config_data
        self.debug = debug
        self.exec_all = exec_all
        cap = self.get_cap(dd)
        # print(cap)
        self.ui = evdev.UInput(cap, name=dev_name)
        self.run()

    async def event_loop(self):
        uri = self.get_uri()
        print("Connecting to: ", uri)
        async with websockets.connect(uri, ssl=self.ssl_context) as websocket:
            if not self.exec_all: await websocket.send(json.dumps({"ident":self.name}))
            async for msg in websocket:
                data = json.loads(msg.replace('\'',"\""))
                print(data)
                if data.get('timestamp'):
                    print(time.time()-float(data.get('timestamp')), data)
                if self.name == data.get('sendto') or self.exec_all:
                    if not self.debug:
                        self.ui.write(data["type"], data["code"], data["value"])
                    else:
                        print("Write event:", data["type"], data["code"], data["value"])
                else:
                    print("Not meant for me!")

    def get_cap(self, dd):
        cap = {}
        if dd:
            print(dd)
            ddl = dd.split(" ")
            for item in ddl:
                if item == "keyboard":
                    cap[e.EV_KEY] = e.keys.keys()
                elif item == "mouse":
                    cap[e.EV_REL] = [
                        e.REL_X,
                        e.REL_Y,
                        e.REL_HWHEEL,
                        e.REL_WHEEL,
                        e.REL_HWHEEL_HI_RES,
                        e.REL_WHEEL_HI_RES
                    ]
                elif item == "trackpad":
                    cap[e.EV_ABS] = [
                        (e.ABS_X, AbsInfo(value=3800, min=1250, max=5631, fuzz=0, flat=0, resolution=59)),
                        (e.ABS_Y, AbsInfo(value=3500, min=1205, max=4834, fuzz=0, flat=0, resolution=81)),
                        (e.ABS_PRESSURE, AbsInfo(value=1, min=0, max=255, fuzz=0, flat=0, resolution=0)),
                        (e.ABS_TOOL_WIDTH, AbsInfo(value=0, min=0, max=15, fuzz=0, flat=0, resolution=0)),
                        (e.ABS_MT_SLOT, AbsInfo(value=0, min=0, max=1, fuzz=0, flat=0, resolution=0)),
                        (e.ABS_MT_POSITION_X, AbsInfo(value=0, min=1250, max=5631, fuzz=0, flat=0, resolution=59)),
                        (e.ABS_MT_POSITION_Y, AbsInfo(value=0, min=1205, max=4834, fuzz=0, flat=0, resolution=81)),
                        (e.ABS_MT_TRACKING_ID, AbsInfo(value=0, min=0, max=65535, fuzz=0, flat=0, resolution=0))
                    ]
                elif item == "stadia":
                    cap[e.EV_KEY] = [
                        e.BTN_SOUTH,
                        e.BTN_EAST,
                        e.BTN_NORTH,
                        e.BTN_WEST,
                        e.BTN_TL,
                        e.BTN_TR,
                        e.BTN_SELECT,
                        e.BTN_START,
                        e.BTN_MODE,
                        e.BTN_THUMBL,
                        e.BTN_THUMBR,
                        e.BTN_TRIGGER_HAPPY1,
                        e.BTN_TRIGGER_HAPPY2,
                        e.BTN_TRIGGER_HAPPY3,
                        e.BTN_TRIGGER_HAPPY4
                    ]
                    cap[e.EV_ABS] = [
                        (e.ABS_X,     AbsInfo(value=128, min=1, max=255, fuzz=0, flat=15, resolution=0)),
                        (e.ABS_Y,     AbsInfo(value=128, min=1, max=255, fuzz=0, flat=15, resolution=0)),
                        (e.ABS_Z,     AbsInfo(value=128, min=1, max=255, fuzz=0, flat=15, resolution=0)),
                        (e.ABS_RZ,    AbsInfo(value=128, min=1, max=255, fuzz=0, flat=15, resolution=0)),
                        (e.ABS_GAS,   AbsInfo(value=0, min=0, max=255, fuzz=0, flat=15, resolution=0)),
                        (e.ABS_BRAKE, AbsInfo(value=0, min=0, max=255, fuzz=0, flat=15, resolution=0)),
                        (e.ABS_HAT0X, AbsInfo(value=0, min=-1, max=1, fuzz=0, flat=0, resolution=0)),
                        (e.ABS_HAT0Y, AbsInfo(value=0, min=-1, max=1, fuzz=0, flat=0, resolution=0))
                    ]

                    pass
        return cap



if __name__=="__main__":
    parser = argparse.ArgumentParser(description="LinuxClient KVM")
    parser.add_argument('-c', '--client', dest="client", action="store", help="Address to connect to")
    parser.add_argument('-n', '--name', dest="name", default=os.uname()[1], action="store", help="Client Name")
    parser.add_argument('-d', '--dev_name', dest="dev_name", default="UInput KVM", action="store", help="Name of device to be created for remote interactions")
    parser.add_argument('--cap', dest="cap", default="mouse keyboard", action="store", help="Description of device to be created for input. [keyboard, mouse, trackpad, stadia]")
    parser.add_argument('--all', dest="exec_all", default=False, action="store_true", help="Execute all recieved commands")

    parser.add_argument('-p', '--port', dest="port", action="store", default="8765", help="Port for server or client to use. Defaults to 8765")
    parser.add_argument('-v', '--verbose', dest="verbose", action="store_true", help="Verbose logging")
    parser.add_argument('--ssl', dest="ssl", action="store", help="Self signed key file for ssl. (.pem) (also not working for me)")
    parser.add_argument('--debug', dest="debug", default=False, action="store_true", help="Enable client debug (will not write events)")

    args = parser.parse_args()

    if args.client:
        lc = LinuxClient(args.client, args.port, args.ssl, args.name, args.dev_name, debug=args.debug, dd=args.cap, exec_all=args.exec_all)
