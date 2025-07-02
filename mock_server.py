import socket
from time import sleep


### Change these variables to suit your application

ssid = ''
password = ''
maxSizeKb = 32
port = 8080
name = ''

class PicoGpioNetDaemon():

    apiVersion = 2
    
    CMD_SET_PIN_SINGLE = 0
    CMD_SET_PIN_MULTI = 1
    CMD_WRITE_BYTES = 2
    CMD_GET_PIN_SINGLE = 3
    CMD_GET_PIN_MULTI = 4
    CMD_DELAY = 5
    CMD_WAIT_FOR_PIN = 6
    CMD_GET_NAME = 7
    CMD_GET_API_VERSION = 8



    def __init__(self, ssid, password, maxSizeKb, name):
        self.ssid = ssid
        self.password = password
        self.name = name
        self.max_read_size = 1024 * maxSizeKb
        self.buffer = bytearray()
        self.client = False
        self.pins = {}
        self.init_spi()

    def init_spi(self):
        pass

    def close(self):
        pass

    def connect(self):
        ip = '127.0.0.1'
        print(f'Connected on {ip}')
        return ip

    def open_socket(self, ip, port):
        address = (ip, port)
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection.bind(address)
        connection.listen(1)
        return connection

    def run_daemon(self, port):

        ip = self.connect()
        serversocket = self.open_socket(ip, port)

        print("Serving data")
        while True:

            print("Awaiting connection")
            (clientsocket, address) = serversocket.accept()
            self.client = clientsocket
            self.buffer = bytearray()

            while True:
                try:
                    result = self.run_command()
                    self.client.send(result)
                except Exception as e:
                    print(e)
                    self.client.close()
                    break

    def run_command(self):

        print("Awaiting command")

        command = self.take_from_buffer_single(1)[0]

        #print(f"Command {command}")

        if command == self.CMD_SET_PIN_SINGLE:
            
            self.cmd_set_pin_single()

        elif command == self.CMD_SET_PIN_MULTI:
            
            self.cmd_set_pin_multi()

        elif command == self.CMD_WRITE_BYTES:

            self.cmd_write_bytes()

        elif command == self.CMD_GET_PIN_SINGLE:

            value = self.cmd_get_pin_single()
            return bytearray([value])

        elif command == self.CMD_GET_PIN_MULTI:

            return self.cmd_get_pin_multi()

        elif command == self.CMD_DELAY:

            self.cmd_delay()

        elif command == self.CMD_WAIT_FOR_PIN:

            self.cmd_wait_for_pin()

        elif command == self.CMD_GET_NAME:

            return self.cmd_get_name()

        elif command == self.CMD_GET_API_VERSION:

            return bytearray([self.apiVersion])

        else:

            print("Unknown")
        
        return bytearray([1])

    def cmd_delay(self):
        print("Delay")

        delay_ms = self.read_length_header(2)
        delay_seconds = float(delay_ms) / 1000.0

        print(f"Seconds: {delay_seconds}")
        sleep(delay_seconds)

    def cmd_wait_for_pin(self):

        print("Wait for pin")

        data = self.take_from_buffer_single(2)
        pin = data[0]
        value = data[1]
        delay_ms = self.read_length_header(2)
        delay_seconds = float(delay_ms) / 1000.0

        while False:
            sleep(delay_seconds)

    def cmd_write_bytes(self):
        print("Write bytes")
        numberOfBytes = self.read_length_header(4)
        for byteArray in self.take_from_buffer(numberOfBytes):
            pass

    def read_spi(self, numberOfBytes):
        return numberOfBytes * [0]

    def cmd_set_pin_single(self):

        print("Set pin")

        # 1 byte. max size: 255
        pair = self.take_from_buffer_single(2)

        self.set_pin(pair)

    def cmd_set_pin_multi(self):

        print("Set pins")
        numberOfPairs = self.read_length_header(1)
        numberOfBytes = numberOfPairs * 2

        for pairs in self.take_from_buffer(numberOfBytes):
            length = len(pairs)
            for i in range(0, length, 2):
                self.set_pin(pairs[i:i+2])

    def set_pin(self, pair):
        pin = pair[0]
        value = pair[1]
        print(f"Setting pin {pin} to {value}")
        self.cache_pin(pin)
        self.pins[pin] = value

    def cache_pin(self, pin):
        if pin not in self.pins:
            self.pins[pin] = 0

    def cmd_get_pin_multi(self):

        print("Get pins")
        numberOfBytes = self.read_length_header(1)
        returnData = bytearray()
        for byteArray in self.take_from_buffer(numberOfBytes):
            for pin in byteArray:
                v = self.get_pin(pin)
                returnData.append(v)
        return returnData

    def cmd_get_pin_single(self):
        print("Get pin single")
        pin = self.take_from_buffer_single(1)
        return self.get_pin(pin[0])

    def get_pin(self, pin):
        print(f"Getting pin {pin}")
        self.cache_pin(pin)
        return self.pins[pin]

    def cmd_get_name(self):
        print(f"Get name ({self.name})")
        nameBytes = self.name.encode()
        nameLength = len(nameBytes)
        nameLengthBytes = nameLength.to_bytes()
        return nameLengthBytes + nameBytes

    def read_length_header(self, numberOfBytes):
        request = self.take_from_buffer_single(numberOfBytes)
        request = bytearray(request)
        intvalue = int.from_bytes(request, 'big')
        return intvalue

    def read_into_buffer(self):
        bytesRead = self.client.recv(self.max_read_size)
        length = len(bytesRead)
        if length == 0:
            raise ValueError('Socket connection closed')
        self.buffer.extend(bytesRead)
        print(f"Read {length} bytes")

    def take_from_buffer_single(self, numberOfBytes):
        returnData = bytearray()
        for loopBytes in self.take_from_buffer(numberOfBytes):
            returnData.extend(loopBytes)
        return returnData

    def take_from_buffer(self, numberOfBytes):
        returnedBytes = 0
        while returnedBytes < numberOfBytes:

            remaining = numberOfBytes - returnedBytes
            bufferLength = len(self.buffer)

            if bufferLength == 0:
                self.read_into_buffer()
                bufferLength = len(self.buffer)

            bytesToRead = min(remaining, bufferLength)
            returnedBytes += bytesToRead
            yield self.buffer[:bytesToRead]
            self.buffer = self.buffer[bytesToRead:]

httpd = PicoGpioNetDaemon(
    ssid = '',
    password = '',
    maxSizeKb = 32,
    name = 'Mock server'
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
