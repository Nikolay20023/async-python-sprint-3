import sys
from asyncio import StreamReader
from collections import deque
from utils import move_back_char, clear_line


async def read_line(stdin_reader: StreamReader):
    def erase_last_char():
        move_back_char()
        sys.stdout.write(' ')
        move_back_char()

    delete_char = b'\x7f'
    input_buffer = deque()
    while (input_char := await stdin_reader.read(1)) != b'\n':
        if input_char == delete_char:
            input_buffer.pop()
            erase_last_char()
            sys.stdout.flush()
        else:
            input_buffer.append(input_char)
            sys.stdout.write(input_char.decode())
    clear_line()
    return b''.join(input_buffer).decode()
