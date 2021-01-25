# uinput-kvm
WIP uinput KVM


## Installation
`pip install -r requirements.txt`

In order for the program to run correctly it needs to have access to the `uinput` system in Linux. This can be accomplished either by just using `sudo` everytime you run the program (for both host and clients!) or by adding the user to the `input` group. The latter process is documented below.

For the `evdev` package to function correctly the user running the command has to be in the `input` user group. You can check what groups your user is in with `groups <username>`. 

You can add a user to a group like so:
`sudo usermod -a -G <group name> <username>`

The documentation for the `evdev` packages states that it is "typically" the `input` group, if this is not the case I wish you luck. 

## Usage
