import network
import machine
from machine import SPI, Pin

class PicoGpioNetDaemon():

    CMD_SET_PIN_SINGLE = 0
    CMD_SET_PIN_MULTI = 1

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

        #print(f"Command {command}")

        if command == self.CMD_SET_PIN_SINGLE:
            
            self.cmd_set_pin_single()

        elif command == self.CMD_SET_PIN_MULTI:
            
            self.cmd_set_pin_multi()

        else:

            print("Unknown")
            #TODO: raise exception
        return bytearray([1])
    """
        CMD_SET_PIN_SINGLE

        Sets the values of one GPIO pin.

        byte[0]: pin
        byte[1]: value

        Example: [16, 0]
        Changes pin 16 to a value of 0
    """
    def cmd_set_pin_single(self):

        print("Set pin")

        # 1 byte. max size: 255
        pair = self.take_from_buffer_single(2)

        self.set_pin(pair)

    """
        CMD_SET_PIN_MULTI

        Sets the values of one or more GPIO pins.

        byte[0]: number of pins to change (max 255)
        byte[1+2*n]: pins
        byte[2+2*n]: values

        The first byte defines the number of pins to be altered.
        The second, fourth, sixth, etc. bytes are pins.
        The third, fifth, seventh, etc. bytes are value.

        So the first byte is how many pin:value pairs there are.
        The remaining bytes are pairs of a pin and a value to set for that pin.

        Example: [2, 16, 0, 18, 1]
        2 pins to change
        first is pin 16, change value to 0
        second is pin 18, change value to 1
    """
    def cmd_set_pin_multi(self):

        print("Set pins")

        # 1 byte. max size: 255
        numberOfPairs = self.read_length_header(1)

        # Read double that, because each pin also has a value paired with it
        numberOfBytes = numberOfPairs * 2

        for pairs in self.take_from_buffer(numberOfBytes):
            length = len(pairs)
            for i in range(0, length, 2):
                self.set_pin(pairs[i])

    """
        Sets a pin to the specified value.

        pair[0] is the number of a pin.
        pair[1] is the value to set that pin to.
    """
    def set_pin(self, pair):
        pin = pairs[i]
        value = pairs[i+1]
        print(f"Setting pin {pin} to {value}")

        self.cache_pin(pin)
        self.pins[pin].value(value)

    def cache_pin(self, pin):
        if pin not in self.pins:
            self.pins[pin] = machine.Pin(pin)
    """
        Reads a header from the socket to determine the length of a request.

        numberOfBytes: the number of bytes to read from the socket
        and interpret as an int.
    """
    def read_length_header(self, numberOfBytes):

        #print("Waiting for length bytes")
        
        request = self.take_from_buffer_single(numberOfBytes)
        #print(f"Received {len(request)} bytes")
        #print(f"Received {request} bytes")

        # Convert from byte[] to bytearray, because micropython
        # won't let from_bytes work with byte[]
        request = bytearray(request)

        # Convert the bytes to an unsigned int
        intvalue = int.from_bytes(request, 'big')
        #print(f"Int: {intvalue}")

        return intvalue

    """
        Reads a number of bytes from the socket into a buffer.
    """
    def read_into_buffer(self):

        # Cap reads at a maximum size of self.max_read_size
        # This is because Pi Pico boards have very little RAM.
        # So we can't necessarily read everything from the buffer
        # in one go.
        bytesRead = self.client.recv(self.max_read_size)
        length = len(bytesRead)

        if length == 0:
            raise ValueError('Socket connection closed')
        self.buffer.extend(bytesRead)
        print(f"Read {length} bytes")

    """
        Takes some bytes from the buffer and returns them.

        numberOfBytes: the number of bytes to take from the buffer.
    """
    def take_from_buffer_single(self, numberOfBytes):
        returnData = bytearray()
        for loopBytes in self.take_from_buffer(numberOfBytes):
            #print(f"Appending {loopBytes}")
            returnData.extend(loopBytes)
        return returnData

    """
        Takes some bytes from the buffer and yields them.

        numberOfBytes: the number of bytes to take from the buffer.
    """
    def take_from_buffer(self, numberOfBytes):
        returnedBytes = 0
        while returnedBytes < numberOfBytes:

            remaining = numberOfBytes - returnedBytes
            bufferLength = len(self.buffer)

            # If the buffer is empty, read more from the socket
            if bufferLength == 0:
                self.read_into_buffer()
                bufferLength = len(self.buffer)

            bytesToRead = min(remaining, bufferLength)
            returnedBytes += bytesToRead
            yield self.buffer[:bytesToRead]
            self.buffer = self.buffer[bytesToRead:]
