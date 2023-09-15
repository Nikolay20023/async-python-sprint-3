import asyncio
import os
import logging
import tty
import sys
from collections import deque
from asyncio import StreamReader, StreamWriter
import utils
from read_line_util import read_line
from message_store import MessageStore
from stdin import create_std_reader


async def send_message(message: str, writer: StreamWriter):
    writer.write((message + '\n').encode())
    await writer.drain()


async def listen_for_messager(
        reader: StreamReader,
        message_store: MessageStore,
):
    while (message := await reader.readline()) != b'':
        await message_store.append(message.decode())
    await message_store.append('Сервер закры соединение')


async def read_and_send(stdin_reader: StreamReader, writer: StreamWriter):
    while True:
        message = await read_line(stdin_reader)
        await send_message(message, writer)


async def main():
    async def redraw_output(items: deque):
        utils.save_cursor_position()
        utils.move_to_top_of_screen()
        for item in items:
            utils.delete_line()
            sys.stdout.write(item)
        utils.restore_cursor_position()

    tty.setcbreak(0)
    os.system('clear')
    rows = utils.move_to_bottom_of_screen()

    messages = MessageStore(redraw_output, rows - 1)

    stdin_reader = await create_std_reader()
    sys.stdout.write('Введите имя пользователя:')
    username = await read_line(stdin_reader)

    reader, writer = await asyncio.open_connection(
        '127.0.0.1', 8000
    )

    writer.write(f'connect {username}\n'.encode())

    await writer.drain()

    message_listener = asyncio.create_task(
        listen_for_messager(
            reader=reader,
            message_store=messages
        )
    )

    input_listener = asyncio.create_task(
        read_and_send(stdin_reader, writer)
    )

    try:
        await asyncio.wait(
            [message_listener, input_listener],
            return_when=asyncio.FIRST_COMPLETED
        )

    except ConnectionAbortedError as ex:
        logging.exception(ex)
        writer.close()
        await writer.wait_closed()


asyncio.run(main())
