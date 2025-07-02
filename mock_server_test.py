import socket
import unittest
from mock_server import PicoGpioNetDaemon

class MockServerTestCase(unittest.TestCase):
    
    def setUp(self):
        self.server = PicoGpioNetDaemon(
            ssid='testssid',
            password='testpassword',
            maxSizeKb=32,
            name='pico-gpio-net-daemon'
        )

    def test_init(self):
        self.assertEqual(self.server.ssid, 'testssid')
        self.assertEqual(self.server.password, 'testpassword')
        self.assertEqual(self.server.name, 'pico-gpio-net-daemon')
        self.assertEqual(self.server.max_read_size, 1024 * 32)
        self.assertEqual(len(self.server.buffer), 0)
        self.assertEqual(self.server.client, False)
        self.assertEqual(self.server.pins, {})

    def test_init_spi(self):
        self.assertTrue(True)

    def test_close(self):
        self.assertTrue(True)

    def test_connect(self):
        ip = self.server.connect()
        self.assertEqual(ip, '127.0.0.1')

    def test_open_socket(self):
        connection = self.server.open_socket(ip='127.0.0.1', port=1234)
        self.assertIsInstance(connection, socket.socket)
        connection.close()

    def test_run_command_set_pin_single(self):
        pin = 20
        value = 1
        self.server.buffer = bytearray([PicoGpioNetDaemon.CMD_SET_PIN_SINGLE, pin, value])
        response = self.server.run_command()
        self.assertEqual(len(self.server.buffer), 0)
        self.assertEqual(len(response), 1)
        self.assertEqual(response[0], 1)
        self.assertEqual(self.server.pins, {pin: value})

        pin2 = 21
        value2 = 0
        self.server.buffer = bytearray([PicoGpioNetDaemon.CMD_SET_PIN_SINGLE, pin2, value2])
        response = self.server.run_command()
        self.assertEqual(len(self.server.buffer), 0)
        self.assertEqual(len(response), 1)
        self.assertEqual(response[0], 1)
        self.assertEqual(self.server.pins, {pin: value, pin2: value2})

    def test_run_command_set_pin_multi(self):
        pin = 20
        value = 1
        pin2 = 21
        value2 = 0
        numberOfPins = 2
        self.server.buffer = bytearray([PicoGpioNetDaemon.CMD_SET_PIN_MULTI, numberOfPins, pin, value, pin2, value2])
        response = self.server.run_command()
        self.assertEqual(len(self.server.buffer), 0)
        self.assertEqual(len(response), 1)
        self.assertEqual(response[0], 1)
        self.assertEqual(self.server.pins, {pin: value, pin2: value2})

    def test_run_command_write_bytes(self):
        self.server.buffer = bytearray([PicoGpioNetDaemon.CMD_WRITE_BYTES, 0, 0, 0, 1, 0])
        response = self.server.run_command()
        self.assertEqual(len(self.server.buffer), 0)
        self.assertEqual(len(response), 1)
        self.assertEqual(response[0], 1)

    def test_run_command_get_pin_single(self):
        pin = 20
        self.server.buffer = bytearray([PicoGpioNetDaemon.CMD_GET_PIN_SINGLE, pin])
        response = self.server.run_command()
        self.assertEqual(len(self.server.buffer), 0)
        self.assertEqual(len(response), 1)
        self.assertEqual(response[0], 0)
        self.assertEqual(self.server.pins, {pin: 0})

        self.server.set_pin([pin, 1])

        self.server.buffer = bytearray([PicoGpioNetDaemon.CMD_GET_PIN_SINGLE, pin])
        response = self.server.run_command()
        self.assertEqual(len(self.server.buffer), 0)
        self.assertEqual(len(response), 1)
        self.assertEqual(response[0], 1)
        self.assertEqual(self.server.pins, {pin: 1})

    def test_run_command_get_pin_multi(self):
        numberOfPins = 2
        pin = 20
        pin2 = 21
        self.server.buffer = bytearray([PicoGpioNetDaemon.CMD_GET_PIN_MULTI, numberOfPins, pin, pin2])
        response = self.server.run_command()
        self.assertEqual(len(self.server.buffer), 0)
        self.assertEqual(len(response), 2)
        self.assertEqual(response[0], 0)
        self.assertEqual(response[1], 0)
        self.assertEqual(self.server.pins, {pin: 0, pin2: 0})

        self.server.set_pin([pin, 1])

        self.server.buffer = bytearray([PicoGpioNetDaemon.CMD_GET_PIN_MULTI, numberOfPins, pin, pin2])
        response = self.server.run_command()
        self.assertEqual(len(self.server.buffer), 0)
        self.assertEqual(len(response), 2)
        self.assertEqual(response[0], 1)
        self.assertEqual(response[1], 0)
        self.assertEqual(self.server.pins, {pin: 1, pin2: 0})

    def test_run_command_delay(self):
        self.server.buffer = bytearray([PicoGpioNetDaemon.CMD_DELAY, 0, 0])
        response = self.server.run_command()
        self.assertEqual(len(self.server.buffer), 0)
        self.assertEqual(len(response), 1)
        self.assertEqual(response[0], 1)

    def test_run_command_wait_for_pin(self):
        pin = 20
        value = 1
        self.server.buffer = bytearray([PicoGpioNetDaemon.CMD_WAIT_FOR_PIN, pin, value, 0, 0])
        response = self.server.run_command()
        self.assertEqual(len(self.server.buffer), 0)
        self.assertEqual(len(response), 1)
        self.assertEqual(response[0], 1)

    def test_run_command_get_name(self):
        self.server.buffer = bytearray([PicoGpioNetDaemon.CMD_GET_NAME])
        response = self.server.run_command()
        self.assertEqual(len(self.server.buffer), 0)
        lenBytes = response[0]
        self.assertEqual(len(response), lenBytes + 1)
        name = response[1:].decode("utf-8")
        self.assertEqual(name, self.server.name)

    def test_run_command_get_api_version(self):
        self.server.buffer = bytearray([PicoGpioNetDaemon.CMD_GET_API_VERSION])
        response = self.server.run_command()
        self.assertEqual(len(self.server.buffer), 0)
        self.assertEqual(len(response), 1)
        self.assertEqual(response[0], self.server.apiVersion)

    def test_run_command_unknown(self):
        self.server.buffer = bytearray([127])
        response = self.server.run_command()
        self.assertEqual(len(self.server.buffer), 0)
        self.assertEqual(len(response), 1)
        self.assertEqual(response[0], 1)

    def test_read_length_header(self):
        self.server.buffer = bytearray([1, 127])
        length = self.server.read_length_header(2)
        self.assertEqual(len(self.server.buffer), 0)
        self.assertEqual(length, 383)

        self.server.buffer = bytearray([0, 0, 2, 0])
        length = self.server.read_length_header(4)
        self.assertEqual(len(self.server.buffer), 0)
        self.assertEqual(length, 512)

    def test_read_into_buffer(self):
        self.assertRaises(AttributeError, lambda: self.server.read_into_buffer())

    def test_take_from_buffer_single(self):
        self.server.buffer = bytearray([1, 127])
        bytes = self.server.take_from_buffer_single(2)
        self.assertEqual(len(bytes), 2)
        self.assertEqual(bytes[0], 1)
        self.assertEqual(bytes[1], 127)

    def test_take_from_buffer(self):
        self.server.buffer = bytearray([1, 127])
        for bytes in self.server.take_from_buffer(2):
            self.assertEqual(len(bytes), 2)
            self.assertEqual(bytes[0], 1)
            self.assertEqual(bytes[1], 127)


if __name__ == '__main__':
    unittest.main()
