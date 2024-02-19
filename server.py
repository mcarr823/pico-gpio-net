import network
import usocket
from time import sleep
import machine
from machine import SPI, Pin

class PicoGpioNetDaemon():

    # Requests are received as byte arrays in a loose format.
    # byte[0] is always a command.
    # The rest of the request changes depending on the command.
    #
    # It is either:
    # [command][length][data]
    # or
    # [command][data]
    #
    # command is always a single byte.
    # length and data may be bigger or smaller depending on the command.
    # See the comments on individual command functions for more info.
    #
    # This format is used due to speed and RAM constraints.
    # Running a proper httpd daemon and using data formats like XML or JSON
    # would add too much overhead.
    #
    # Note that commands can be chained together in a continuous stream.
    # So if you send through multiple commands, one after the other, in a
    # single stream of bytes, then it will handle all of them sequentially.
    #
    # For example:
    # cmd1 = [1, 1, 16, 1]
    # cmd2 = [2, 0, 0, 4, 0, ...]
    # cmd3 = [1, 1, 16, 0]
    # cmd = [*cmd1, *cmd2, *cmd3]
    #
    # In the above, three different commands have been joined together into
    # a single byte array.
    #
    # cmd1 sets pin 16 to HIGH (1).
    # cmd2 writes data to SPI.
    # cmd3 sets pin 16 to LOW (0).
    #
    # By sending through all three in one go (cmd) we can avoid the extra
    # overhead of making and waiting on multiple network requests.

    
    CMD_SET_PIN_SINGLE = 0
    CMD_SET_PIN_MULTI = 1
    CMD_WRITE_BYTES = 2
    CMD_GET_PIN_SINGLE = 3
    CMD_GET_PIN_MULTI = 4
    CMD_DELAY = 5
    CMD_WAIT_FOR_PIN = 6



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

        elif command == self.CMD_WRITE_BYTES:

            self.cmd_write_bytes(numberOfBytes)

        elif command == self.CMD_GET_PIN_SINGLE:

            result = self.cmd_get_pin_single(pin)
            return bytearray([result])

        elif command == self.CMD_GET_PIN_MULTI:

            return self.cmd_get_pin_multi()

        elif command == self.CMD_DELAY:

            self.cmd_delay()

        elif command == self.CMD_WAIT_FOR_PIN:

            self.cmd_wait_for_pin()

        else:

            print("Unknown")
            #TODO: raise exception
        
        # Default return value.
        # Most of these functions write values instead of reading them,
        # so we just return a single byte to say we're done.
        return bytearray([1])

    """
        CMD_DELAY

        Delays execution of the thread for a given number of milliseconds.
        This might be used when you want to send multiple commands to the
        Pico at once, but enforce a delay between them.

        eg. If command #1 performs some kind of hardware initialization,
        and it needs to finish before command #2 can run.
        This way those two commands can still be sent in the same request,
        but executed with a suitable delay between them.

        byte[0]: first byte of the delay
        byte[1]: second byte of the delay

        Example: [2, 5]
        first delay byte: 2 (00000010)
        second delay byte: 5 (00000101)

        The delay bytes (00000010 00000101) converted to a big endian int
        give a value of 517.

        So in this example, we tell the Pico to wait for 517 milliseconds
        before moving on to the next command.
    """
    def cmd_delay(self):
        print("Delay")

        # 2 bytes. max size: 65535
        delay_ms = self.read_length_header(2)
        delay_seconds = float(delay_ms) / 1000.0

        print(f"Seconds: {delay_seconds}")
        sleep(delay_seconds)

    """
        CMD_WAIT_FOR_PIN

        Waits for a specific pin to reach a specific value.
        For example, to wait for the BUSY pin to have a value of 0,
        signifying that the GPIO device is no longer busy.

        The Pico will periodically re-check the state of the pin
        based on the `delay` value set in the request.

        byte[0]: pin to read
        byte[1]: desired value
        byte[2]: first byte of the delay
        byte[3]: second byte of the delay

        Example: [8, 1, 2, 5]
        pin to read: 8
        value to wait for: 1
        first delay byte: 2 (00000010)
        second delay byte: 5 (00000101)

        The delay bytes (00000010 00000101) converted to a big endian int
        give a value of 517.

        So in this example, we wait for pin 8 to have a value of 1.
        We re-check the pin every 517 milliseconds until the value is 1.
    """
    def cmd_wait_for_pin(self):

        print("Wait for pin")

        data = self.take_from_buffer_single(2)
        pin = data[0]
        value = data[1]

        # 2 bytes. max size: 65535
        delay_ms = self.read_length_header(2)
        delay_seconds = float(delay_ms) / 1000.0

        while self.get_pin(pin) != value:
            sleep(delay_seconds)

    """
        CMD_WRITE_BYTES

        Writes a bunch of raw byte data over SPI.

        byte[0]: first length byte
        byte[1]: second length byte
        byte[2]: third length byte
        byte[3]: fourth length byte
        byte[4...]: raw byte data to write over SPI

        The first four bytes are a big-endian int which define the size
        of the request.
        The remaining bytes, with a length equal to that int, are written
        directly to spidev.

        Example: [0, 0, 4, 0, ...]
        Length of [0, 0, 4, 0] (00000000 00000000 00000100 00000000)
        which equals 1024 when converted to a big-endian int.
        The remaining bytes, which should be 1024 in length, are the data
        to write to spidev.
    """
    def cmd_write_bytes(self):

        print("Write bytes")

        # 4 bytes. max size: 4,294,967,295
        numberOfBytes = self.read_length_header(4)

        #print(f"Writing {numberOfBytes} bytes")
        for byteArray in self.take_from_buffer(numberOfBytes):
            self.spi.write(byteArray)

        #print(f"Finished writing")

    def read_spi(self, numberOfBytes):
        return self.spi.read(numberOfBytes)

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
        CMD_GET_PIN_MULTI

        Returns a list containing the states of multiple pins

        byte[0]: number of pins to read (max 255)
        byte[1...]: pins to read

        Example: [2, 16, 18]
        pins to read: 2
        first pin: 16
        second pin: 18
    """
    def cmd_get_pin_multi(self):

        print("Get pins")

        # 1 byte. max size: 255
        numberOfBytes = self.read_length_header(1)

        returnData = bytearray()
        for byteArray in self.take_from_buffer(numberOfBytes):
            for pin in byteArray:
                v = self.get_pin(pin)
                returnData.append(v)
        return returnData

    """
        CMD_GET_PIN_SINGLE

        Returns the value of a single pin

        byte[0]: pin to read

        Example: [18]
        This request would read a single pin: 18
        It would then return the state of that pin as an int.
    """
    def cmd_get_pin_single(self):

        print("Get pin single")

        # Pin to read
        pin = self.take_from_buffer_single(1)

        return self.get_pin(pin)

    def get_pin(self, pin):
        print(f"Getting pin {pin}")
        self.cache_pin(pin)
        return self.pins[pin].value()

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
