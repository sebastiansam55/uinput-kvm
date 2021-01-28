# uinput-kvm
UInput "KVM". Note that the KVM portion is in quotes!

## Limitations/Notes
10ms lag from computer to VM. Looks like about 20-30ms lag over local network (wifi to wired device)

I wouldn't recommend using something like this on anything but a local network for both latency and **security** issues!!!

Seriously don't use this for anything but fun. Basically without ssl (which I can't get working) any one on the network would be able to send input to your machine.

I haven't done extensive (read any) testing on what is gonna happen when the devices that are being listened to are lost or disconnected (unplug/reboot). My guess would be that the program wouldn't like it. 

Also I'm not even sure how accurate the quoted 10ms lag time is because I have also been able to get negative numbers from the `<timestamp sent>-time.time()`.


## Installation
`pip install -r requirements.txt`

In order for the program to run correctly it needs to have access to the `uinput` system in Linux. This can be accomplished either by just using `sudo` every time you run the program (for both host and clients!) or by adding the user to the `input` group. The latter process is documented below.

For the `evdev` package to function correctly the user running the command has to be in the `input` user group. You can check what groups your user is in with `groups <username>`. 

You can add a user to a group like so:
`sudo usermod -a -G <group name> <username>`

The documentation for the `evdev` packages states that it is "typically" the `input` group, if this is not the case I wish you luck. 

I would also recommend a full restart to ensure that the user group changes take effect.

I also had to `chmod 660 /dev/uinput` on my testing VM and reboot again. Not quite sure why.

I'm not entirely sure that the second part will be necessary, it may have been something in the code that was misbehaving.

## Usage
Dang so there are alot of options huh. We're going to start from the top and work our way down the options. Flag requirements are described via: [S]erver/[C]lient/[O]ptional.

| Flag | Description | Required |
| :--: | :---------: | :-------------------------------: |
| `-c, --client` | The IP address the "remote" machine should connect to. | [C] |
| `-n --name` | The name of the client to transmit to the server. Used in the config file. Defaults to hostname | [CO] |
| `-s --server` | Address for the server to bind to (typically found with `ifconfig`) | [S] |
| `-m --mouse` | Path of the mouse device to grab. | [S] |
| `-k --keyboard` | Path of the keyboard device to grab. | [S] |
| `--controller` | Path of the controller device to grab. | [S] |
| `-d --dev_name` | Name to use for the new input device | [CO] |
| `-p --port` | Port to listen/connect to. Default 8765 | [CSO] |
| `-v --verbose` | Will give you more information than you need.  | [CSO] |
| `-g --grab` | Exclusively grab the devices | [SO] |
| `-ls --list` | Lists the devices connected to the computer. | [standalone] |
| `--config` | A json file described in the section below. | [CS] |
| `--ssl` | Implemented ssl support according to docs. Does not work for me. | [CSO] |
| `--debug` | Debug for clients, operates everything but actually writing events. | [CO] |
| `--default` | The default name to send signals to. | [SO] |
| `-b --broadcast` | Send signals to all clients. | [SO] |


For `-m`, `-k` and `--controller` flags you can describe the device that you want to capture either with it's name, path or the digit associated with it (ie if you wanted to grab `event10` put `10`) You can see the paths and names of devices by running `-ls`.

Note that if you grab a device by it's path that may change depending. The name is generally the more reliable way to grab the device.

## Config file
The program takes a `json` file passed to it via `--config`. In this file you can (sort of) define the hotkeys used to swap between kvm clients.

Provided below is the config file I use for testing.
```json
{
    "modifiers": [29, 42, 56],
    "hotkeys": [
        ["test", 2],
        ["test2", 3],
        [<hostname>,4]
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

You can add the name your "server" to the list. Selecting this by default or hotkey just ungrabs the devices, allowing them to act normally on the "server" computer.

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

`/usr/bin/python3 /path/to/kvm.py -s 192.168.0.22 -p 8765 -m /dev/input/event5 -k /dev/input/event3 -g`

Note that if you use `sudo crontab` you need to make sure all the same python packages the script uses are also installed for the `root` user.

Then on each host machine install another cron job in a similar fashion;

`@reboot /path/to/script`

where your remote scripts should look something like this;

`python3 kvm.py -c 192.168.0.22 -p 8765 `

## Windows Client
The windows client uses boppreh's [keyboard](https://github.com/boppreh/keyboard) and [mouse](https://github.com/boppreh/mouse) modules. Big shout-out for those libraries (and all others!). I never program on Windows with python and these made it down right easy to implement (with one or two minor hitches! no h-scroll for one!)

For the windows client in addition to `keyboard` and `mouse` you also need `websockets`. Installing these is pretty much the same process as on linux; assuming you have `python` installed and in your execution path;

```python
python3 -m pip install keyboard
python3 -m pip install mouse
python3 -m pip install websockets
```

Starting the client should be more or less identical to the Linux version:

`python3 win_client.py -c 192.168.0.10 -p 8765 --name windows`

If you don't use the `--name` flag the program will default to using the name derived from `os.environ['COMPUTERNAME']` which by default is something like `DESKTOP-A2D9OA`.

Again the `--verbose` flag does nothing... yet!

Sometimes clicking with the mouse seems to hang the windows client? I'm not sure very intermittent could have been caused by something it was doing in testing/development. Might also be related to running in a VM with virtualbox additions enabled. Not sure!

## MacOS client
Relies on `websockets`, `pynput`. These packages can be installed as described above.

Rough draft. MacOS seems to handle modifiers differently as well. I'll get around to completing implementation, it will probably be having to hand code a bunch of stuff instead of justing a lookup table.

The mouse works great, including drag-and-select. Keyboard sort of works. There is a list of the keys on my (laptop) keyboard that I couldn't easily find translations for. Feel free to open a PR/Issue if you know some more about this.

## RPi0
I use a RPi0 to either route my stadia controller to my main Linux computer or use a wired keyboard that I have converted to be "wireless" (taping the RPi0 and a battery to the keyboard and setting a cron job to run at boot to launch the program.)

The RPi0 was chugging pretty hard with the `linux_client.py`, even when very stripped down. Because of this (and because latency is obviously a major factor) I wrote a lightweight client that uses `websockets-client` instead of the `websockets`. The difference is night and day.

I also turned off the RPi0 wireless power saving mode `sudo iwconfig wlan0 power off` and threw that into the crontab too. Probably not necessary but better safe than sorry.

I won't say that it is lag free but I was able to play a few different games without major issues. 

The keyboard forwarding works great imo. There are some stability issues but they should reconnect without too much down time. It's a WIP for sure.

## TODO
- Move away from `json` module (v. slow) to `str(data)`.
    + Have to do some timing tests but leaning towards `str`

- Maybe swap all clients to `websocket` `create_connection`. It seems much more light weight.

- https://stackoverflow.com/questions/4162642/single-vs-double-quotes-in-json
Maybe?