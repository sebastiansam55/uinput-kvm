import keyboard
import mouse
import asyncio
import websockets
import sys
import json
import argparse
import os
import time
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
from asyncio.exceptions import CancelledError


parser = argparse.ArgumentParser(description="WindowsClient KVM")
parser.add_argument('-c', '--client', dest="client", action="store", help="Address to connect to")
parser.add_argument('-n', '--name', dest="name", default=os.environ['COMPUTERNAME'], action="store", help="Client Name")
parser.add_argument('-d', '--dev_name', dest="dev_name", default="UInput KVM", action="store", help="Name of device to be created for remote interactions")
parser.add_argument('-p', '--port', dest="port", action="store", default="8765", help="Port for server or client to use. Defaults to 8765")
parser.add_argument('-v', '--verbose', dest="verbose", action="store_true", help="Verbose logging")
parser.add_argument('--ssl', dest="ssl", action="store", help="Self signed key file for ssl. (.pem) (also not working for me)")
parser.add_argument('--debug', dest="debug", default=False, action="store_true", help="Enable client debug (will not write events)")

args = parser.parse_args()

class WindowsClient():
    def __init__(self, address, port, ssl_filename, name, debug=False):
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
        self.debug = debug
        self.run()

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

    async def event_loop(self):
        uri = self.get_uri()
        print("Connecting to: ", uri)
        async with websockets.connect(uri, ssl=self.ssl_context) as websocket:
            await websocket.send(json.dumps({"ident":self.name}))
            async for msg in websocket:
                data = json.loads(msg)
                print(time.time()-float(data['timestamp']), data)
                if self.name == data['sendto']:
                    if not self.debug:
                        if data['type'] == 1 and not self.is_btn(data): #e.KEY event
                            if data['value'] == 1: #down
                                keyboard.press(data['code'])
                            elif data['value'] == 0: #up
                                keyboard.release(data['code'])
                            print("WindowsClient Keyboard write:", data['code'])
                        elif data['type'] == 2:
                            print("WindowsClient Mouse write:", data['code'], data['value'])
                            if data['code'] == 0: #REL_X
                                mouse.move(data['value'],0, absolute=False)
                            elif data['code'] == 1: #REL_Y
                                mouse.move(0,data['value'], absolute=False)
                            elif data['code'] == 8: #scroll wheel
                                mouse.wheel(data['value'])
                            elif data['code'] == 6: #hscroll wheel
                            # mouse.move(x,y, absolute=False)
                                print("Horizontal scrolling not supported :(")
                                pass
                        if self.is_btn(data):
                            #mouse button
                            if data['code'] in mouse_btn_map: #left,right, middle
                                m_btn = mouse_btn_map[data['code']]
                                print(m_btn)
                                if data['value'] == 1: #down
                                    mouse.press(m_btn)
                                elif data['value'] == 0: #up
                                    mouse.release(m_btn)
                        



                    else:
                        print("Write event:", data["type"], data["code"], data["value"])
                        print("do_press: ", do_press, "do_release: ", do_release)
                else:
                    print("Not meant for me!")

    def is_btn(self, data):
        btn = [272,273,274,275,276,277,278,279]
        if data['type'] == 1:
            if data['code'] in btn:
                return True
        return False


    # async def windows_write(self, message, )
# Event code 272 (BTN_LEFT) -> mouse.LEFT
# Event code 273 (BTN_RIGHT) -> mouse.RIGHT
# Event code 274 (BTN_MIDDLE) -> mouse.MIDDLE
# Event code 275 (BTN_SIDE)
# Event code 276 (BTN_EXTRA)
# Event code 277 (BTN_FORWARD)
# Event code 278 (BTN_BACK)
# Event code 279 (BTN_TASK)


mouse_btn_map = {
    272: mouse.LEFT,
    273: mouse.RIGHT,
    274: mouse.MIDDLE,
}

if args.client:
    #have to call this in order for scan codes to work right
    keyboard.key_to_scan_codes('b')
    wc = WindowsClient(args.client, args.port, args.ssl, args.name, args.debug)