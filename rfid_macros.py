import argparse
import asyncio
import evdev
from evdev import UInput, ecodes as e
import yaml
import functools
from collections import defaultdict

from typing import Iterable

TASKS = {}
CONFIG = defaultdict(lambda: {'mode': 'async'})

async def shell_exec(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return stdout, stderr


def shell_exec_future(cmd):
    asyncio.ensure_future(shell_exec(cmd))


async def generate_kb_input(keys=None):
    if not keys:
        raise ValueError("Can't iterate over nothing")
    ui = UInput()
    for k in keys:
        if isinstance(k, str) and ',' in k:
            for state in [1, 0]:
                for kk in k.split(','):
                    kk = e.__getattribute__('KEY_' + kk)
                    print("SENDING KEY", kk)
                    ui.write(e.EV_KEY, kk, state)
                ui.syn()
        else:
            if isinstance(k, str):
                k = e.__getattribute__('KEY_' + k)
            print("SENDING KEY", k)
            ui.write(e.EV_KEY, k, 1)
            ui.write(e.EV_KEY,k, 0)
            ui.syn()
    ui.close()


async def execute_task(line):
    task = TASKS.get(line)
    if task:
        await task()
    else:
        print(f"Task not found {line}")


async def read_device(device):
    with device.grab_context():
        read_line=''
        async for event in device.async_read_loop():
            cat_event = evdev.categorize(event)
            if isinstance(cat_event, evdev.events.KeyEvent):
                if cat_event.keystate == 1:
                    k = cat_event.keycode.lstrip('KEY_')
                    if k != 'NTER':
                        read_line += k
                    else:
                        asyncio.create_task(execute_task(read_line))
                        read_line=''


async def parse_macros_function(func: dict, task_id: str):
    if func.get('send_key'):
        return await generate_kb_input([func['send_key']])
    if func.get('sleep'):
        return await asyncio.sleep(func['sleep'])
    if func.get('mode'):
        CONFIG[task_id]['mode'] = func['mode']


async def parse_macro_command(command, task_id):
    print(command)
    if isinstance(command, str):
        return await shell_exec(command)
    elif isinstance(command, dict):
        return await parse_macros_function(command, task_id)
    elif isinstance(command, Iterable):
        async def command_func():
            for v in command:
                coro = parse_macro_command(v, task_id)
                if CONFIG[task_id]['mode'] == 'async':
                    asyncio.create_task(coro)
                else:
                    await coro
        return await command_func()


def parse_macros(macros: dict):
    for task_id, command in macros.items():
        TASKS[task_id] = functools.partial(parse_macro_command, command=command, task_id=task_id)


def main():
    parser = argparse.ArgumentParser(description='RFID Macros')
    parser.add_argument(
        '-d', '--device', action='store', dest='devices',
        type=str, nargs='*', help='Path to RFID device files',
    )
    parser.add_argument(
        'macros', type=str,
        help='Path to macros YAML file'
    )
    args = parser.parse_args()
    with open(args.macros, 'r') as f:
        macros = parse_macros(yaml.safe_load(f))
    devices = [
        evdev.InputDevice(d)
        for d in args.devices
    ]
    for device in devices:
        asyncio.ensure_future(read_device(device))

    loop = asyncio.get_event_loop()
    loop.run_forever()


if __name__ == "__main__":
    main()
