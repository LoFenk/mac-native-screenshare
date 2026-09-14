"""Bounded TCP-to-Unix relay: only peers on the selected private LAN reach VNC."""
import asyncio
import ipaddress
import socket


def allowed_peer(address, subnet):
    try:
        peer = ipaddress.IPv4Address(address)
        network = ipaddress.IPv4Network(subnet)
        return peer in network and peer not in (network.network_address, network.broadcast_address)
    except ValueError:
        return False


class Relay:
    def __init__(self, listener, backend, subnet, limit=8):
        self.listener = listener
        self.backend = str(backend)
        self.subnet = subnet
        self.limit = limit
        self.tasks = set()
        self.writers = set()
        self.server = None

    async def copy(self, source, destination):
        while data := await source.read(65536):
            destination.write(data)
            await destination.drain()

    async def client(self, reader, writer):
        task = asyncio.current_task()
        peer = writer.get_extra_info('peername')
        if len(self.tasks) >= self.limit or not peer or not allowed_peer(peer[0], self.subnet):
            writer.close()
            await writer.wait_closed()
            return
        self.tasks.add(task)
        self.writers.add(writer)
        backend_writer = None
        copies = []
        try:
            backend_reader, backend_writer = await asyncio.wait_for(asyncio.open_unix_connection(self.backend, limit=65536), 3)
            self.writers.add(backend_writer)
            copies = [asyncio.create_task(self.copy(reader, backend_writer)),
                      asyncio.create_task(self.copy(backend_reader, writer))]
            await asyncio.wait(copies, return_when=asyncio.FIRST_COMPLETED)
        except (OSError, asyncio.TimeoutError, ConnectionError):
            pass
        finally:
            for copy in copies:
                copy.cancel()
            await asyncio.gather(*copies, return_exceptions=True)
            for connection in (writer, backend_writer):
                if connection:
                    connection.close()
                    self.writers.discard(connection)
            self.tasks.discard(task)

    async def start(self):
        self.listener.setblocking(False)
        self.server = await asyncio.start_server(self.client, sock=self.listener, limit=65536)

    async def close(self):
        if self.server:
            self.server.close()
        else:
            self.listener.close()
        for writer in tuple(self.writers):
            writer.close()
        for task in tuple(self.tasks):
            task.cancel()
        await asyncio.gather(*tuple(self.tasks), return_exceptions=True)
        if self.server:
            await self.server.wait_closed()


def reserve(address, port):
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((address, port))
        listener.listen(8)
        return listener
    except BaseException:
        listener.close()
        raise
