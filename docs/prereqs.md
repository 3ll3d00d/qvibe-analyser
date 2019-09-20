## Bill of Materials

### Recorder

1) a Raspberry Pi model with wireless connectivity, there are currently 3 options:

- [raspberry pi 3](https://www.raspberrypi.org/products/raspberry-pi-3-model-b/)
- [raspberry pi 4](https://www.raspberrypi.org/products/raspberry-pi-4-model-b/)
- [raspberry pi zero w](https://www.raspberrypi.org/products/raspberry-pi-zero-w/)

2) an rpi case that lets you access the GPIO pins, e.g. [the pibow](https://shop.pimoroni.com/collections/pibow)

3) any reputable class 10 Micro SD card card, 4GB minimum, such as this [sandisk](https://www.amazon.co.uk/SanDisk-Android-microSDHC-Memory-Adapter/dp/B013UDL5RU/) model, note that

- note that the maximum size supported is 32GB
- maximum read/write speed is about 25MB/s so there is no point spending on UHS3 cards

4) An [MPU-6050 IMU](http://playground.arduino.cc/Main/MPU-6050#boards), one per raspberry pi

5) [i2c cables](https://www.amazon.co.uk/Dupont-wire-cable-color-1p-1p-connector/dp/B0116IZ0UO) which are also known as

- [jumper jerky](https://shop.pimoroni.com/products/jumper-jerky) 
- [dupont cables](https://www.meccanismocomplesso.org/en/jumper-dupont-wires-a-practical-solution-for-arduino-and-breadboards/) 

6) a lightweight but secure mounting mechanism for attaching the board to the seat without weighing it down

- the best mechanism to use will vary with seating material, examples include

    - [foam tape](https://www.amazon.co.uk/gp/product/B016YS4JKS/ref=oh_aui_search_detailpage?ie=UTF8&psc=1)
    - [dolls house wax](http://www.dollshouse.com/tacky-wax)

### Analyser

1) A computer attached to the same network as the raspberry pi

## Getting Ready for Installation

### Install a SSH (Secure Shell) Client

SSH is secure shell, it's a standard way to securely login to a remote (\*nix) host.

Linux users should need no introduction to this.

MacOS users can familiarise themselves with the [terminal app](http://www.macworld.co.uk/feature/mac-software/get-more-out-of-os-x-terminal-3608274/)

Windows users have to install a [3rd party client](http://www.htpcbeginner.com/best-ssh-clients-windows-putty-alternatives/2/) such as [MobaXterm](https://mobaxterm.mobatek.net/)

Android users can consider an app like [connectbot](https://play.google.com/store/apps/details?id=org.connectbot&hl=en_GB)
or one of the [many options on the play store](https://play.google.com/store/search?q=ssh&c=apps&hl=en_GB)

iOS users no doubt have something appropriate in their app store ([sample google search](https://www.google.co.uk/?q=ios+ssh+client)).

### Install a SCP (Secure Copy) Client

scp provides a simple and easy way to copy a file over a ssh connection, it is the recommended way to transfer files to and from your rpi.

For Linux and OSX users, scp is available via your shell.

For Windows users, [MobaXterm](https://mobaxterm.mobatek.net/) provides a drag and drop file transfer facility. [WinSCP](https://winscp.net/eng/index.php) is an alternative which provides a Windows Explorer style interface.
