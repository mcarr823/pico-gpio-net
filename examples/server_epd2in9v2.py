from machine import Pin, SPI
from server import PicoGpioNetDaemon

"""
    Epd2in9v2PicoGpioNetDaemon

    This is an example of how to setup a gpio net daemon based
    on the Epd2in9v2 Pico HAT per:
    https://github.com/waveshareteam/Pico_ePaper_Code/blob/main/python/Pico_ePaper-2.9.py

    Based on the spec from Waveshare, what we need in order to make
    the daemon work with that HAT is to setup the right pins in a
    specific way.
    The rest of the code should already work as-is.

    Given that the pin setup is the only thing which needs to change,
    we can get away with only overriding init_spi, and that is
    enough to make this daemon work with the HAT.

    Of course, we still need the client to send the right byte data
    TO the Pico in order for this to work.
    This example only covers the server (this program), not the client.
"""

class Epd2in9v2PicoGpioNetDaemon(PicoGpioNetDaemon):

    def init_spi(self):

        self.pins[12] = Pin(12, Pin.OUT) # REST
        self.pins[13] = Pin(13, Pin.IN, Pin.PULL_UP) # BUSY
        self.pins[9] = Pin(9, Pin.OUT) # CS

        self.spi = SPI(1, baudrate=4000_000)

        self.pins[8] = Pin(8, Pin.OUT) # DC



# Create an instance of the daemon class.
# This creates the object and connects to the SPI device,
# but does not connect to a network.
httpd = Epd2in9v2PicoGpioNetDaemon(
    ssid = 'MY_WIFI_SSID',
    password = 'MY_WIFI_PASSWORD',
    maxSizeKb = 32,
    name = 'My Pico'
)

try:

    # Connects the daemon to a network and starts listening
    # on the given port for incoming data connections.
    # Runs indefinitely until keyboard interrupt.
    httpd.run_daemon(port = 8080)

except KeyboardInterrupt:

    # Release the resources held by the daemon and stop listening
    # for incoming connections.
    httpd.close()
