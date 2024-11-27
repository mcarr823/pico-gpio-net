import socket

"""
    This class provides a way for other applications to integrate with
    pico-gpio-net.
    Simply copy and paste this client.py file into your project, then
    create an instance of the PicoGpioNetClient and use it.


    Take note of the way autoFlush works and consider whether your project
    should handle flushing itself or not.
    This client is built with the concept of queueing messages and not
    sending them until .flush() is called (unless autoFlush is True), or
    a read operation is performed.

    Messages are queued in this way for the purpose of increasing speed.
    So your client can queue up a lot of messages and send them through
    all in one chunk, rather than performing small individual reads/writes.

    This is better in terms of performance because of:
    1) network packet sizing, and
    2) network latency.

    Of course, it ultimately depends on your application.
    If you send a lot of small requests in quick succession, then you're
    better off calling flush manually.
    If you do requests infrequently, however, or the speed of the application
    doesn't particularly matter (eg. a dashboard which refreshes every hour),
    then you might as well turn autoFlush on.
"""

class PicoGpioNetClient:

    # These variables should always match the ones in server.py
    CMD_SET_PIN_SINGLE = 0
    CMD_SET_PIN_MULTI = 1
    CMD_WRITE_BYTES = 2
    CMD_GET_PIN_SINGLE = 3
    CMD_GET_PIN_MULTI = 4
    CMD_DELAY = 5
    CMD_WAIT_FOR_PIN = 6
    CMD_GET_NAME = 7
    CMD_GET_API_VERSION = 8

    # Socket connection
    sock = False

    # Outgoing data queue
    queue = bytearray()

    # Size of queue
    queueCount = 0

    # Whether to flush the queue automatically or not
    autoFlush = False

    """
        ip: ip address of the Pico server to connect to

        port: port on which the Pico server is listening

        autoFlush: if True, send commands immediately.
        If False, queue up commands until .flush() is called.
    """
    def __init__(self, ip, port, autoFlush = False):
        self.autoFlush = autoFlush
        sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_IP, socket.IP_TTL, 1)
        sock.connect((ip, port))
        self.sock = sock

    """
        Closes the socket connection, if open.
        Otherwise does nothing.
    """
    def close(self):
        try:
            if self.sock:
                self.sock.close()
        except Exception as e:
            # Already closed
            pass

    """
        Flushes the queue.
        This sends all pending requests to the server in one go.
        It then receives (and discards) all of the server responses.
    """
    def flush(self):
        if self.queueCount == 0:
            return
        print(f"Flushing: {self.queueCount}")
        self.sock.send(self.queue)
        results = []
        result = bytearray()
        while len(result) < self.queueCount:
            diff = self.queueCount - len(result)
            #print(f"Reading {diff} more bytes")
            result.extend(self.sock.recv(diff))
        #print(f"Received: {result}")
        expected = b'\x01'
        for i in range(0, self.queueCount):
            success = result[i] == 1
            #print(f"Result {i}: {success}")
            results.append(success)
        self.queue = bytearray()
        self.queueCount = 0

    """
        Queues up an arbitrary write request.

        A write request is one which doesn't expect any meaningful
        data in response.
        For example, a request which either succeeds or fails, and
        doesn't provide any further insight into the operation
        beyond that.

        `cmd` Array of bytes to send
    """
    def do_write_request(self, cmd):
        self.queue.extend(bytearray(cmd))
        self.queueCount += 1
        #print(f"Queue count: {self.queueCount}")
        if self.autoFlush:
        	self.flush()

    """
        Performs a read request after flushing the queue, if needed.

        A read request is one which expects a meaningful response.
        For example, reading data from SPI, or reading a pin's state.

        `cmd` Array of bytes to send
        `length` Expected length of the response from the server
    """
    def do_read_request(self, cmd, length):
        self.flush()
        self.sock.send(bytearray(cmd))
        return self.sock.recv(length)

    """
        Sets the state of a single pin.

        `pin` The number of the pin to change the state of
        `value` New value to set for the pin
    """
    def set_pin(self, pin, value):
        cmd = [self.CMD_SET_PIN_SINGLE, pin, value]
        return self.do_write_request(cmd)

    """
        Sets the states of multiple pins.

        `pinsAndValues` Array of pin:value pairs.
        eg. [ [16,1], [18,0] ]
        would set pin 16 to value 1, and pin 18 to value 0.
    """
    def set_pins(self, pinsAndValues):
        numberOfPins = len(pinsAndValues)
        cmd = [self.CMD_SET_PIN_MULTI, numberOfPins]
        for (pin, value) in pinsAndValues:
            cmd.extend([pin, value])
        return self.do_write_request(cmd)

    """
        Retrieves the value of a single pin.

        `pin` Pin to read the value of

        Returns the value of that pin.
    """
    def get_pin(self, pin):
        numberOfPins = 1
        print(f"Get pin {pin}")
        cmd = [self.CMD_GET_PIN_SINGLE, pin]
        return self.do_read_request(cmd, 1)

    """
        Retrieves the value of multiple pins.

        `pins` Array of pins to read the values of

        Returns an array of pin values, in order.

        eg. If you send pins [16,18] and got a response of [0,1]
        then that means pin 16 has value 0, and pin 18 has value 1.
    """
    def get_pins(self, pins):
        numberOfPins = len(pins)
        print(f"Getting {numberOfPins} pins")
        cmd = [self.CMD_GET_PIN_MULTI, numberOfPins, *pins]
        return self.do_read_request(cmd, numberOfPins)

    """
        Sends raw byte data to write over SPI.

        `bytedata` Array of bytes to write to the SPI device
    """
    def write_bytes(self, bytedata):
        print("Pico write bytes")
        print(f"Length: {len(bytedata)}")
        lengthBytes = len(bytedata).to_bytes(4, 'big')
        cmd = [self.CMD_WRITE_BYTES, *lengthBytes, *bytedata]
        return self.do_write_request(cmd)

    """
        Tells the Pico server to wait for a defined amount of time
        before moving onto the next request.

        This is useful when sending through multiple commands in a
        single packet.

        For example, let's say your GPIO device requires you to wait
        for 10ms after setting a pin before writing SPI data.

        One way of doing this would be for your client application to
        send a SET_PIN command, wait 10ms, then send a WRITE_BYTES command.

        Another way of doing this would be to send a SET_PIN command, a
        DELAY command, and a WRITE_BYTES command all in one packet.

        The second approach sends 3 commands instead of 2, but it does so
        in 1 packet instead of 2, making it faster overall due to network
        latency and packet size constraints.

        `delay_ms` Time to wait in milliseconds
    """
    def delay(self, delay_ms):
        print(f"Sending delay of {delay_ms}")
        delayBytes = delay_ms.to_bytes(2, 'big')
        cmd = [self.CMD_DELAY, *delayBytes]
        print(f"Sending {cmd}")
        return self.do_write_request(cmd)

    """
        Waits for a given pin to reach a particular value before
        continuing execution.

        This is useful for waiting until a GPIO device is in a particular
        state before trying to send it more commands.

        eg. Waiting until the BUSY pin is set to 0, indicating that the
        GPIO device has finished whatever it was doing, before trying to
        make it do something else.

        `pin` Pin to wait on
        `value` Value to wait for the pin to reach
        `delay_ms` Milliseconds to wait between pin reads 
    """
    def wait_for_pin(self, pin, value, delay_ms):
        print("Sending delay")
        delayBytes = delay_ms.to_bytes(2, 'big')
        cmd = [self.CMD_WAIT_FOR_PIN, pin, value, *delayBytes]
        return self.do_write_request(cmd)

    """
        Asks the Pico device to identify itself.

        The first byte returned by the Pico is the length of the name.
        The remaining bytes are the encoded name.

        Command introduced in API version 2.
    """
    def get_name(self):
        print("Getting device name")
        cmd = [self.CMD_GET_NAME]
        lengthBytes = self.do_read_request(cmd, 1)
        length = int.from_bytes(lengthBytes)
        nameBytes = self.sock.recv(length)
        return nameBytes.decode()

    """
        Asks the Pico device which version of pico-gpio-net it is running.

        The API version is used to identify which commands the Pico is
        able to understand and respond to.

        Command introduced in API version 2.

        Note that although it was introduced in version 2, this command
        "accidentally" works in version 1 as well, since the default
        response for an unknown command is [1].
    """
    def get_api_version(self):
        print(f"Getting API version")
        cmd = [self.CMD_GET_API_VERSION]
        bytes = self.do_read_request(cmd, 1)
        return int.from_bytes(bytes)
