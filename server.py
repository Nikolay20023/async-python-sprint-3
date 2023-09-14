import asyncio
import logging
from asyncio import StreamReader, StreamWriter


class Server:
    """Chast_server."""
    def __init__(self, host="127.0.0.1", port=8000):
        self._host = host
        self._port = port
        self._username_to_write = []

    async def _start_server(self):
        server = await asyncio.start_server(
            self._client_connected,
            self._host,
            self._port
        )
        async with server:
            await server.serve_forever()

    async def _client_connected(self,
                                reader: StreamReader, writer: StreamWriter):
        command = await reader.readline()
        print(f'CONNECTED {reader} {writer}')
        command, args = command.split(b' ')
        if command == b'connect':
            username = args.replace(b'\n', b'')
            await self._add_user(username, reader, writer)

    async def _on_connect(self, username, writer: StreamWriter):
        writer.write(
            'Добро пожаловать!\n'.encode()
        )
        await writer.drain()
        await self._notify_all(
            f'Подключился {username}\n'
        )

    async def _add_user(self, username: str,
                        reader: StreamReader, writer: StreamWriter):
        self._username_to_write[username] = writer
        asyncio.create_task(self._listen_for_messages(
            username,
            reader
        ))

    async def _remove_user(self, username):
        writer: StreamWriter = self._username_to_write[writer]
        del self._username_to_write[username]
        try:
            writer.close()
            await writer.wait_closed()
        except ConnectionRefusedError as ex:
            logging.exception(
                'Ошибка при закрытие клиентского серевера',
                exc_info=ex
            )

    async def _listen_for_messages(self, username: str, reader: StreamReader):
        try:
            while (
                data := await asyncio.wait_for(reader.readline(), 60)
            ) != b'':
                await self._notify_all(f'{username}: {data.decode()}')
                await self._notify_all(f'{username} has left the chat\n')
        except asyncio.exceptions.TimeoutError as ex:
            logging.exception(
                'Ошибка при чтение данных',
                exc_info=ex
            )

    async def _notify_all(self, message: str):
        inactive_user = []
        for username, writer in self._username_to_write:
            try:
                writer.write(message.encode())
                await writer.drain()
            except ConnectionError as ex:
                logging.exception(
                    'Ошибка при записи данных клиенту',
                    exc_info=ex
                )
                inactive_user.append(username)
        [await self._remove_user(user) for user in inactive_user]


async def main():
    """main."""
    chat_server = Server()
    await chat_server._start_server()

asyncio.run(main())
