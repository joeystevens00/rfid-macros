### RFID Macros

Execute arbitrary commands when a tag is read.

#### Commands YAML Example
```
"0000000008": notify-send $(curl -s https://blockchain.info/ticker | jq -r '.USD."15m"')
"0000000009":
  - atom ~/dev/proj1 ~/dev/proj2 ~/dev/proj3
  - firefox https://stackoverflow.com/
"0000000010":
  send_key: SPACE
```


#### Usage
```
python3 rfid_macros.py commands.yaml -d /dev/input/by-id/usb-Some_RFID_Reader_event-kbd
```


#### Avoid running as root

Take ownership of the device so the script doesn't have to be run as root
```
sudo chown user:user /dev/input/by-id/usb-Some_RFID_Reader_event-kbd
```

Take ownership of uinput to send keyboard events (send_key event)
```
sudo chown user:user /dev/uinput
```
