import argparse
import asyncio
import evdev
from evdev import UInput, ecodes as e
import yaml

from typing import Iterable

TASKS = {}


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


def generate_kb_input(keys=None):
    if not keys:
        raise ValueError("Can't iterate over nothing")
    ui = UInput()
    for k in keys:
        if isinstance(k, str):
            k = e.__getattribute__(k)
        ui.write(e.EV_KEY, k, 1)
        ui.write(e.EV_KEY,k, 0)
        ui.syn()
    ui.close()


async def execute_task(line):
    task = TASKS.get(line)
    if task:
        task()
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


def parse_macros_function(func: dict):
    if func.get('send_key'):
        return lambda: generate_kb_input(['KEY_' + func['send_key']])


def parse_macro_command(command):
    if isinstance(command, str):
        return lambda: shell_exec_future(command)
    elif isinstance(command, dict):
        return parse_macros_function(command)
    elif isinstance(command, Iterable):
        commands = []
        for v in command:
            commands.append(parse_macro_command(v))
        def command_func():
            for c in commands:
                c()
        return command_func


def parse_macros(macros: dict):
    for task_id, command in macros.items():
        TASKS[task_id] = parse_macro_command(command)


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
