# pico-gpio-net

## What is it?

This program is made to run on a Raspberry Pi Pico WH with MicroPython.

It enables a Pico to receive some basic GPIO commands over a network connection.


## Why would I want to do that?

To remotely control a Pico-connected GPIO device, such as a LED HAT or a display panel.

For example, you could connect a set of LEDs to your Pico, then turn them on or off from your computer, effectively giving you a wifi-controlled light.


## How does it work?

This program opens a TCP socket connection on port 8080.

When a client connects to that port, this program then waits for a command to execute.

This program will then continue to wait for further commands from the client and will not accept any new connections until the current client disconnects.

A client can send commands one at a time, or send through multiple commands simultaneously to achieve better latency.


## How do I use it?

### Pico (server) setup

First, you'll need to decide how you want to run this program. You can either:
1. use PicoGpioNetDaemon directly, or
2. subclass the daemon
An example of the second approach can be found in examples/server*.py

Second, you'll need to edit your daemon. At the bare minimum you'll need to set the SSID and password for your Wifi network.
At that stage you should try running the daemon via Thonny while the Pico is connected to your computer. That way you can make sure that it's able to connect to the Wifi network.

Third, you may need to modify the daemon to suit your needs. You might be able to skip this step if the default implementation is already satisfactory. Some hardware may require you to change the baudrate of the SPI device, for instance, or to setup specific ports. This will vary depending on what GPIO device you're interfacing with.

Finally, you'll need to put the code on your Pico and make it run your daemon automatically when the Pico powers on.

That should be it for the Pico (server) setup. Next, you need to send commands to the daemon from your computer (client) to make it actually do something.

### Computer (client) setup

This part is going to vary depending on what device you've attached to the Pico, and how you want to interact with it.

But ultimately, you will need to write a program, or adapt an existing one, to make it send commands to the Pico server in a format it understands.

You can do this by taking the class from client.py and integrating it with your program.

See examples/client*.py for a simple example of how to use the client library.
