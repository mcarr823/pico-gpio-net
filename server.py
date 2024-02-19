import network
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

    """
        Connects to a wifi network and returns the IP address
        assigned to this device.

        This function will continue trying to connect indefinitely
        until it succeeds.
    """
    def connect(self):
        #Connect to WLAN
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        wlan.connect(self.ssid, self.password)
        while wlan.isconnected() == False:
            print('Waiting for connection...')
            sleep(1)
        print(wlan.ifconfig())
        ip = wlan.ifconfig()[0]
        print(f'Connected on {ip}')
        return ip

    """
        Opens a socket and listens for incoming connections.

        Returns the socket connection.
    """
    def open_socket(self, ip, port):
        # Open a socket
        address = (ip, port)
        connection = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM)
        connection.bind(address)
        connection.listen(1)
        return connection
