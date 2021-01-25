# uinput-kvm
UInput "KVM". Note that the KVM portion is in quotes! 10ms lag from computer to VM.

## TODO
Have to add some way for the server to distinguish between who is sending things and who they should be sent to.

Probably going to have clients identify with a name (`--name`) and local devices identify similarly via the first info sent to the server.

Have to add some way to swap between what client is sent the info. Probably going to modify `event_loop` and have it send the name of the device the events should be sent to. And use the same loop to listen for hotkeys to change the client being sent to. 

## Limitations/Notes
WebSockets are alright. I have yet to test this on anything but a single client local VM back and forth.

Because of the implementation you can't really connect from your own IP address, I guess this would extend to WAN applications? Not sure. I wouldn't recommend using something like this on anything but a local network for both latency and security issues.

I haven't done extensive (read any) testing on what is gonna happen when the devices that are being listened to are lost or disconnected (unplug/reboot). My guess would be that the program wouldn't like it. 

Also I'm not even sure how accurate the quoted 10ms lag time is because I have also been able to get negative numbers from the `<timestamp sent>-time.time()`.

The program only grabs devices via paths right now so that might mean that they could change between reboots. I will probably implement an alternate means of selection later. 


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
| `-n --name` | The name of the client to transmit to the server. Unused currently | [CO] |
| `-s --server` | Address for the server to bind to (typically found with `ipconfig`) | [S] |
| `-m --mouse` | Path of the mouse device to grab. | [S] |
| `-k --keyboard` | Path of the keyboard device to grab. | [S] |
| `-d --dev_name` | Name to use for the new input device | [CO] |
| `-p --port` | Port to listen/connect to. Default 8765 | [CSO] |
| `-v --verbose` | Doesn't do anything right now | [CSO] |
| `-g --grab` | Exclusively grab the devices | [SO] |
| `-l --list` | Lists the devices connected to the computer. | [standalone] |
| `--ssl` | Implemented ssl support according to docs. Does not work for me. | [CSO] |


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