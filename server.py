import asyncio
import logging
from asyncio import StreamReader, StreamWriter
from asyncio import AbstractServer
from config import Setting


class Server:
    """Сервер основанный на транспортных потоках."""
    def __init__(self, host, port):
        self._host: str = host
        self._port: int = port
        self._username_to_write = {}

    async def _start_server(self) -> None:
        """Запустить сервер с помощью asyncio.strat_Server
        И обслуживать запросы бесконечно."""
        server: AbstractServer = await asyncio.start_server(
            self._client_connected,
            self._host,
            self._port
        )
        async with server:
            await server.serve_forever()

    async def _client_connected(self,
                                reader: StreamReader, writer: StreamWriter):
        """При подключение нового клиента добавить
        его в состояние сервера. Обработать команду."""
        command = await reader.readline()
        logging.info('CONNECTED %s %s', reader, writer)
        command, args = command.split(b' ')
        if command == b'connect':
            username = args.replace(b'\n', b'').decode()
            self._add_user(username, reader, writer)
            await self._on_connect(username, writer)

    async def _on_connect(self, username: str, writer: StreamWriter):
        """При подключение по приветсвовать нового клиента
        и сообщить всем пользователям об подлючении """
        writer.write(
            'Добро пожаловать!\n'.encode()
        )
        await writer.drain()
        await self._notify_all(
            f'Подключился {username}\n',
            username
        )

    def _add_user(self, username: str,
                  reader: StreamReader, writer: StreamWriter):
        """Добавить  по username поток чтение и записи """
        if not (username in self._username_to_write):
            self._username_to_write[username] = [writer, reader]
            asyncio.create_task(self._listen_for_messages(
                username,
                reader
            ))
        else:
            asyncio.create_task(self._listen_for_messages(
                username,
                self._username_to_write[username][1]
            ))

    async def _remove_user(self, username):
        """Удалить потоки пользователя и разорвать подключение."""
        writer: StreamWriter = self._username_to_write[username][0]
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
        """Подключем поток чтение и ждём сообщение от этого потока
        всё это в бесконечном цикле
        как только приходит сообщение обрабатываем, выводим сообщения """
        try:
            while (
                data := await asyncio.wait_for(reader.readline(), 60)
            ) != b'':
                await self._notify_all(f'{username}:{data.decode()}', username)
            await self._notify_all(f'{username} has left the chat\n', username)
        except asyncio.exceptions.TimeoutError as ex:
            logging.exception(
                'Ошибка при чтение данных',
                exc_info=ex
            )

    async def _notify_all(self, message: str, user: str):
        """Сообщим всем пользователям какие либо сообщения
        одновременно удаля инактивных пользователей"""
        inactive_user = []
        for username, list_wr_rd in self._username_to_write.items():
            try:
                if user != username:
                    list_wr_rd[0].write(message.encode())
                    await list_wr_rd[0].drain()
            except ConnectionError as ex:
                logging.exception(
                    'Ошибка при записи данных клиенту',
                    exc_info=ex
                )
                inactive_user.append(username)
        [await self._remove_user(user) for user in inactive_user]


async def main():
    """Запуск сервера"""
    settings = Setting()
    chat_server = Server(settings.host, settings.port)
    await chat_server._start_server()

asyncio.run(main())
