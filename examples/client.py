import socket
from ../client import PicoGpioNetClient

"""
	This is a quick example script which connects to
	a Pico server, reads a pin, tries to change its
	value, waits, then reads it again.

	It doesn't have any real purpose except to provide
	a simple example of how to use the PicoGpioNetClient
	class.
"""


# IP address and port of the Pico server
# we want to connect to.
ip = '192.168.1.7'
port = 8080

# Set auto-flush to true
autoFlush = True

# Define a random pin to read for this test
REST_PIN = 12

client = False

try:
	# First, create the client object.
	# This will auto-connect and throw an exception
	# if the connection fails.
	client = PicoGpioNetClient(ip, port, autoFlush)

	# Read the REST_PIN
	rest_value = client.get_pin(REST_PIN)

	# If the rest value is 0, set it to 1
	if rest_value == 0:
		client.set_pin(REST_PIN, 1)

	# Wait 100ms
	client.delay(100)

	# Read the pin again
	rest_value = client.get_pin(REST_PIN)

	# Verify that it changed
	if rest_value == 1:
		# Value changed successfully
		pass

except Exception as e:

	# Probably a connection exception
	print(e)

finally:

	if client:
		# Make sure to close the socket connection after you're done
		client.close()
