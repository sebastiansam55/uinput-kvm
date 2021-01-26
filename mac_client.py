import asyncio
import websockets
import sys
import json
import argparse
import os
import time
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
from asyncio.exceptions import CancelledError
from pynput import keyboard as kb
from pynput.keyboard import KeyCode as kc
from pynput import mouse as mou
from pynput.mouse import Button



#huge shout out to this page for having a translation table!!
#http://web.archive.org/web/20100501161453/http://www.classicteck.com/rbarticles/mackeyboard.php

parser = argparse.ArgumentParser(description="WindowsClient KVM")
parser.add_argument('-c', '--client', dest="client", action="store", help="Address to connect to")
parser.add_argument('-n', '--name', dest="name", default=os.uname()[1], action="store", help="Client Name")
parser.add_argument('-p', '--port', dest="port", action="store", default="8765", help="Port for server or client to use. Defaults to 8765")
parser.add_argument('-v', '--verbose', dest="verbose", action="store_true", help="Verbose logging")
parser.add_argument('--ssl', dest="ssl", action="store", help="Self signed key file for ssl. (.pem) (also not working for me)")
parser.add_argument('--debug', dest="debug", default=False, action="store_true", help="Enable client debug (will not write events)")

args = parser.parse_args()

class MacClient():
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
                            try:
                                keyCode = kc(key_translate[data['code']])
                                if data['value'] == 1: #down
                                    keyboard.press(keyCode)
                                elif data['value'] == 0: #up
                                    keyboard.release(keyCode)
                                print("MacClient Keyboard write:", data['code'], keyCode)
                            except KeyError as err:
                                print("Code not found in map: ",data['code'],err)
                        elif data['type'] == 2:
                            print("MacClient Mouse write:", data['code'], data['value'])
                            if data['code'] == 0: #REL_X
                                mouse.move(data['value'],0)
                            elif data['code'] == 1: #REL_Y
                                mouse.move(0,data['value'])
                            elif data['code'] == 8: #scroll wheel
                                mouse.scroll(data['value'])
                            # elif data['code'] == 6: #hscroll wheel
                            # # mouse.move(x,y, absolute=False)
                            #     print("Horizontal scrolling not supported :(")
                            #     pass
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

key_translate = {
    103:126,
    108:125,
    105:123,
    106:124,
    14:117,
    28:76,
    102:115,
    107:119,
    109:121,
    104:116,
    111:51,
    15:48,
    57:49,
    139:58,
    1:53,
    58:57,
    138:114,
    59:122,
    60:120,
    61:99,
    62:118,
    63:96,
    64:97,
    65:98,
    66:100,
    67:101,
    68:109,
    87:103,
    88:111,
    16:12,
    17:13,
    18:14,
    19:15,
    20:17,
    21:16,
    22:32,
    23:34,
    24:31,
    25:35,
    32:2,
    33:3,
    34:5,
    35:4,
    36:38,
    37:40,
    38:37,
    44:6,
    45:7,
    46:8,
    47:9,
    48:11,
    49:45,
    50:46,
    11:29,
    2:18,
    3:19,
    4:20,
    5:21,
    6:23,
    7:22,
    8:26,
    9:28,
    10:25,
    52:47,
    51:43,
    53:44,
    82:82,
    79:83,
    80:84,
    81:85,
    75:86,
    76:87,
    77:88,
    71:89,
    72:91,
    73:92,
    55:67,
    78:69,
    74:78,
    98:75,
    83:65,
    30:0
}

mouse_btn_map = {
    272: Button.left,
    273: Button.right,
    274: Button.middle,
}


mouse = mou.Controller()

keyboard = kb.Controller()

if args.client:
    mc = MacClient(args.client, args.port, args.ssl, args.name, args.debug)