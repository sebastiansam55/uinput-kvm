# uinput-kvm
UInput "KVM". Note that the KVM portion is in quotes!

## Limitations/Notes
10ms lag from computer to VM. Looks like about 20-30ms lag over local network (wifi to wired device)

This was created in under 48 hours. Not battle tested.

WebSockets are alright. I have yet to test this on anything but a single client local VM back and forth.

Because of the implementation you can't really connect from your own IP address, I guess this would extend to WAN applications? Not sure. I wouldn't recommend using something like this on anything but a local network for both latency and security issues.

I haven't done extensive (read any) testing on what is gonna happen when the devices that are being listened to are lost or disconnected (unplug/reboot). My guess would be that the program wouldn't like it. 

Also I'm not even sure how accurate the quoted 10ms lag time is because I have also been able to get negative numbers from the `<timestamp sent>-time.time()`.

The program only grabs devices via paths right now so that might mean that they could change between reboots. I will probably implement an alternate means of selection later. 

Note also that the program broadcasts all commands to all connected clients and just changes one of the values in the payload at allow the client to determine if it needs to write the event.


## Installation
`pip install -r requirements.txt`

In order for the program to run correctly it needs to have access to the `uinput` system in Linux. This can be accomplished either by just using `sudo` every time you run the program (for both host and clients!) or by adding the user to the `input` group. The latter process is documented below.

For the `evdev` package to function correctly the user running the command has to be in the `input` user group. You can check what groups your user is in with `groups <username>`. 

You can add a user to a group like so:
`sudo usermod -a -G <group name> <username>`

The documentation for the `evdev` packages states that it is "typically" the `input` group, if this is not the case I wish you luck. 

I would also recommend a full restart to ensure that the user group changes take effect.

I also had to `chmod 660 /dev/uinput` on my testing VM and reboot again. Not quite sure why.

I'm not entirely sure that the second part will be necessary, it may have been something in the code that was misbehaving

## Usage
Dang so there are alot of options huh. We're going to start from the top and work our way down the options. Flag requirements are described via: [S]erver/[C]lient/[O]ptional.

| Flag | Description | Required |
| :--: | :---------: | :-------------------------------: |
| `-c, --client` | The IP address the "remote" machine should connect to. | [C] |
| `-n --name` | The name of the client to transmit to the server. Used in the config file. Defaults to hostname | [CO] |
| `-s --server` | Address for the server to bind to (typically found with `ipconfig`) | [S] |
| `-m --mouse` | Path of the mouse device to grab. | [S] |
| `-k --keyboard` | Path of the keyboard device to grab. | [S] |
| `-d --dev_name` | Name to use for the new input device | [CO] |
| `-p --port` | Port to listen/connect to. Default 8765 | [CSO] |
| `-v --verbose` | Doesn't do anything right now | [CSO] |
| `-g --grab` | Exclusively grab the devices | [SO] |
| `-ls --list` | Lists the devices connected to the computer. | [standalone] |
| `--config` | A json file described in the section below. | [CS] |
| `--ssl` | Implemented ssl support according to docs. Does not work for me. | [CSO] |
| `--debug` | Debug for clients, operates everything but actually writing events. | [CO] |

Note that there currently isn't much (any) difference between what happens in the `-k` or `-m` flags. They are currently interchangeable.


## Config file
The program takes a `json` file passed to it via `--config`. In this file you can (sort of) define the hotkeys used to swap between kvm clients.

Provided below is the config file I use for testing.
```json
{
    "modifiers": [29, 42, 56],
    "hotkeys": [
        ["test", 2],
        ["test2", 3]
    ]
}
```

The `modifiers` section describes the keys that should be held down in order to trigger the listen for change of KVM client. They are stored as `int` values that `evdev` can understand. This can get a bit confusing as "1" is an int value of `2`. Here is a table that lists the common modifiers and their `int` values. 
To see all of the keys that `evdev` recognizes you can run the following in your python console;
Note that the tab completion is a great feature here, use `e.KEY_LEFT` to see all of the modifiers that start with left. In general the names used are self explanatory. Note that they are all described by their "lowercase" versions (e.g. there is a `KEY_PERIOD` not a `KEY_GREATERTHAN`).

```
from evdev import ecodes as e
e.KEY
```

| Key | ecodes | int value |
| :-: | :----: | :-------: |
| Left Shift | KEY_LEFTSHIFT | 42 |
| Right Shift | KEY_RIGHTSHIFT | 54 |
| Left Ctrl | KEY_LEFTCTRL | 29 |
| Right Ctrl | KEY_RIGHTCTRL | 97 |
| Left Alt | KEY_LEFTALT | 56 |
| Right Alt | KEY_RIGHTALT | 100 |
| Left Meta | KEY_LEFTMETA | 125 |
| Right Meta | KEY_RIGHTMETA | 126 |

You are on your own for determining other codes.

The next part of the config file is the `hotkeys` section. This section is a list of lists in the form of `[<clientname>, <ecodes key to swap to them>]`. The `clientname` is going to be either the name you specified for the client with `--name` or the computer's hostname if no `--name` flag was used. The ecodes key should be an `int` corresponding to the key that you want to press in combination with the modifiers (as described above) to swap to sending outputs to.

## SSL
In order to enable ssl you need to have a self signed certificate that you can distribute to all of the computers. 

I followed [this](https://serverfault.com/questions/889581/how-to-generate-a-pem-certificate-in-an-easy-way-for-testing) guide to generate `.pem` files. 

`openssl req -new -newkey rsa:4096 -nodes -keyout kvm.key -out kvm.csr`

then 

`openssl x509 -req -sha256 -days 365 -in kvm.csr -signkey kvm.key -out kvm.pem`

In theory at least. I implemented it as described [here](https://websockets.readthedocs.io/en/stable/intro.html#secure-example) but have not been able to get it working for now.

## Run at boot?
Because it is a one file script you can easily add it to cron on boot. Whether you want to do this is a conversation you should have with yourself before anyone else. If you have conferred and made a decision here is the easiest way to add it:

On the server KVM machine you should make a script that is just your single line launch command. The add this to cron with `crontab -e`

`@reboot /path/to/script`

where your script should look something like this;

`python3 kvm.py -s 192.168.0.22 -p 8765 -m /dev/input/event5 -k /dev/input/event3 -g`

Note that if you use `sudo crontab` you need to make sure all the same python packages the script uses are also installed for the `root` user.

Then on each host machine install another cron job in a similar fashion;

`@reboot /path/to/script`

where your remote scripts should look something like this;

`python3 kvm.py -c 192.168.0.22 -p 8765 `

## TODO
Check that mouse stuff is working as expected with regular mice (it seems trackpoint doesn't work great)

Add way to ungrab local devices upon hotkey. Would also need to regrab upon other hotkeys!