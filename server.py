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

    """
        This function is the main content loop and should be run
        in order to kick everything off.
        It connects to wifi, opens a socket, waits for connections, then
        handles the received data.
    """
    def run_daemon(self, port):

        # Connect to wifi, get an IP address from the router
        ip = self.connect()

        # Open a socket connection
        serversocket = self.open_socket(ip, port)

        print("Serving data")
        while True:

            print("Awaiting connection")

            # Wait for a client to connect
            (clientsocket, address) = serversocket.accept()
            
            # Client has connected
            self.client = clientsocket
            
            # Flush the buffer, in case of previous connection aborting
            self.buffer = bytearray()

            # Wait indefinitely for data from the client.
            # Stop if the client disconnects, or if execution is
            # interrupted.
            while True:
                try:

                    # Perform a command in response to data from the client
                    result = self.run_command()

                    # Send a response to the client
                    self.client.send(result)

                except Exception as e:
                    print(e)

                    # Close the socket connection
                    self.client.close()

                    # Break the while loop and wait for a new client
                    break

    """
        This function waits for byte data from a client and
        handles the data accordingly by calling the expected
        function.

        It returns a byte array, which is sent back to the client.
    """
    def run_command(self):

        print("Awaiting command")

        command = self.take_from_buffer_single(1)[0]
        return bytearray([1])
