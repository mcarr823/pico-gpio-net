import machine

class PicoGpioNetDaemon():


    def __init__(self, ssid, password, maxSizeKb):
        self.ssid = ssid
        self.password = password

        # Maximum number of bytes to read in a single loop iteration.
        # The Pi Pico has 264kB of SRAM, so let's make it smaller than that...
        self.max_read_size = 1024 * maxSizeKb

        self.buffer = bytearray()
        self.client = False

        self.pins = {}
        self.init_spi()

    """
        Setup pins as needed and initialize SPI device.
        This function can be overridden by a subclass of
        PicoGpioNetDaemon in order to customize the default
        pin setup, change the SPI settings, and so on.
    """
    def init_spi(self):
        self.spi = machine.SPI(1, baudrate=4000_000)

    """
        Release the SPI interface, pins, and any other resources
        being held.
    """
    def close(self):
        self.spi.deinit()
        machine.reset()
