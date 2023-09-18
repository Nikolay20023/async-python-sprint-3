import asyncio
import os
import logging
from collections import deque
from asyncio import StreamReader
import utils
from read_line_util import read_line
from message_store import MessageStore
from stdin import create_std_reader


class Client:
    def __init__(self, host, port) -> None:
        self._host = host
        self._port = port
        self.reader = None
        self._username = None
        self.writer = None
        self.messages = None

    async def on_connect(self):
        self.reader, self.writer = await asyncio.open_connection(
            self._host, self._port
        )

    async def send_message(self, message: str):
        self.writer.write((message + '\n').encode())
        await self.writer.drain()

    async def listen_for_messager(
            self,
            reader: StreamReader,
            message_store: MessageStore,
    ):
        while (message := await reader.readline()) != b'':
            await message_store.append(message.decode())
        await message_store.append('Сервер закрыл соединение')

    async def read_and_send(
            self,
            stdin_reader: StreamReader,
    ):
        while True:
            message = await read_line(stdin_reader)
            await self.send_message(message)

    async def run(self):
        async def redraw_output(items: deque):
            utils.save_cursor_position()
            utils.move_to_top_of_screen()
            for item in items:
                utils.delete_line()
                print(item)
            utils.restore_cursor_position()

        os.system('clear')
        rows = utils.move_to_bottom_of_screen()

        self.messages = MessageStore(redraw_output, rows - 1)

        stdin_reader = await create_std_reader()
        print('Введите имя пользователя:')
        username = await read_line(stdin_reader)

        await self.on_connect()

        self.writer.write(f'connect {username}\n'.encode())

        await self.writer.drain()

        message_listener = asyncio.create_task(
            self.listen_for_messager(
                reader=self.reader,
                message_store=self.messages
            )
        )

        input_listener = asyncio.create_task(
            self.read_and_send(stdin_reader)
        )

        try:
            await asyncio.wait(
                [message_listener, input_listener],
                return_when=asyncio.FIRST_COMPLETED
            )

        except ConnectionAbortedError as ex:
            logging.exception(ex)
            self.writer.close()
            await self.writer.wait_closed()


async def main():
    client = Client('127.0.0.1', 8000)
    await client.run()

asyncio.run(main())
