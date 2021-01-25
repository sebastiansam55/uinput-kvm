import asyncio
import websockets
import sys
import json



async def hello():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        while True:
            msg = await websocket.recv()
            data = json.loads(msg)
            print(data)
        

asyncio.get_event_loop().run_until_complete(hello())
asyncio.get_event_loop().run_forever()