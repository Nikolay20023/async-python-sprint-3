import asyncio
import os
import logging
from collections import deque
from asyncio import StreamReader, StreamWriter
import utils
from read_line_util import read_line
from message_store import MessageStore
from stdin import create_std_reader
from config import Setting


class Client:
    def __init__(self, host, port) -> None:
        self._host: str = host
        self._port: int = port
        self.reader: StreamReader = None
        self._username: str = None
        self.writer: StreamWriter = None
        self.messages: MessageStore = None

    async def on_connect(self):
        """Получаем reader writer посредством подключение соединения """
        self.reader, self.writer = await asyncio.open_connection(
            self._host, self._port
        )

    async def send_message(self, message: str):
        """Отправить сообщение по StreamWiter."""
        self.writer.write((message + '\n').encode())
        await self.writer.drain()

    async def listen_for_messager(
            self,
            reader: StreamReader,
            message_store: MessageStore,
    ):
        """Прослушивать сообщение от сервера
        и добавлять их в хранилище сообщений."""
        while (message := await reader.readline()) != b'':
            await message_store.append(message.decode())
        await message_store.append('Сервер закрыл соединение')

    async def read_and_send(
            self,
            stdin_reader: StreamReader,
    ):
        """Считать сообщение с помощью переопределённого stdin_reader."""
        while True:
            message = await read_line(stdin_reader)
            await self.send_message(message)

    async def run(self):
        """Основная логика Client
        """
        async def redraw_output(items: deque):
            """Обратный вызов который
            перемещает курсор в начало экрана перерисовыввет
            экран и возвращает в начало"""
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
    """Запуск клиента"""
    settings = Setting()
    client = Client(settings.host, settings.port)
    await client.run()

asyncio.run(main())
