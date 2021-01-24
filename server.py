import websockets
import asyncio
import threading


class Server(threading.Thread):
    def __init__(self, in_q, out_q):
        threading.Thread.__init__(self, args=(), kwargs=None)
        self.in_q = in_q
        self.out_q = out_q
        pass

    async def listen(self, websocket, path):
        async for message in websocket:
            print(message)
            self.out_q.put(message)
        # data = await websocket.recv()
        # self.out_q.put(data)
        print(in_q)
        for item in iter(self.in_q.get, None):
            print(item)
            await websocket.send()

    def run(self):
        loop = asyncio.new_event_loop()
        start_server = websockets.serve(self.listen, "localhost", 8765, loop=loop)

        loop.run_until_complete(start_server)
        loop.run_forever()