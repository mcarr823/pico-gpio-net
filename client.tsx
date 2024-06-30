/**
 * This class provides a way for NodeJS applications to integrate with
 * pico-gpio-net.
 * 
 * Copy and paste this client.tsx file into your project, then
 * create an instance of the PicoGpioNetClient and use it.
 * 
 * Note that you will need to make modifications to it depending on your
 * application.
 * eg. To integrate with your application's socket library and buffer implementation.
 * 
 * 
 * Also, take note of the way autoFlush works and consider whether your project
 * should handle flushing itself or not.
 * This client is built with the concept of queueing messages and not
 * sending them until .flush() is called (unless autoFlush is True), or
 * a read operation is performed.
 * 
 * Messages are queued in this way for the purpose of increasing speed.
 * So your client can queue up a lot of messages and send them through
 * all in one chunk, rather than performing small individual reads/writes.
 * 
 * This is better in terms of performance because of:
 * 1) network packet sizing, and
 * 2) network latency.
 * 
 * Of course, it ultimately depends on your application.
 * If you send a lot of small requests in quick succession, then you're
 * better off calling flush manually.
 * If you do requests infrequently, however, or the speed of the application
 * doesn't particularly matter (eg. a dashboard which refreshes every hour),
 * then you might as well turn autoFlush on.
 */
export default class PicoGpioNetClient{

    // These variables should always match the ones in server.py
    CMD_SET_PIN_SINGLE = 0
    CMD_SET_PIN_MULTI = 1
    CMD_WRITE_BYTES = 2
    CMD_GET_PIN_SINGLE = 3
    CMD_GET_PIN_MULTI = 4
    CMD_DELAY = 5
    CMD_WAIT_FOR_PIN = 6

    // Socket connection
    sock = False

    // Outgoing data queue
    queue: Buffer

    // Size of queue
    queueCount: number

    // Whether to flush the queue automatically or not
    autoFlush: boolean

    /**
     * @param ip: ip address of the Pico server to connect to
     * @param port: port on which the Pico server is listening
     * @param  autoFlush: if True, send commands immediately.
     * If False, queue up commands until .flush() is called.
    */
    constructor(
        ip,
        port,
        autoFlush = false
    ){
        
        this.autoFlush = autoFlush
        this.queueCount = 0
        this.queue = Buffer.alloc()

        this.sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        this.setsockopt(socket.SOL_IP, socket.IP_TTL, 1)
        this.sock.connect((ip, port))

    }

    /**
     * Closes the socket connection, if open.
     * Otherwise does nothing.
     */
    close(){
        try{
            this.sock.close()
        }catch(e){
            // Already closed
        }
    }

    /**
     * Flushes the queue.
     * This sends all pending requests to the server in one go.
     * It then receives (and discards) all of the server responses.
     */
    flush(){

        if (this.queueCount == 0)
            return

        console.log(`Flushing: ${this.queueCount}`)
        this.sock.send(this.queue)
        const results = Array<boolean>()
        const result = Array<Buffer>()
        while (result.length < this.queueCount){
            const diff = this.queueCount - result.length
            // console.log(`Reading ${diff} more bytes`)
            result.push(this.sock.recv(diff))
        }
        // console.log(`Received: ${result}`)
        const expected = b'\x01'
        for (var i = 0; i < this.queueCount; i += 1){
            const success = result[i] == 1
            // print(`Result ${i}: ${success}`)
            results.push(success)
        }
        this.queue = bytearray()
        this.queueCount = 0
    }

    /**
     * Queues up an arbitrary write request.
     * 
     * A write request is one which doesn't expect any meaningful
     * data in response.
     * For example, a request which either succeeds or fails, and
     * doesn't provide any further insight into the operation
     * beyond that.
     * 
     * @param cmd Array of bytes to send
    */
    do_write_request(
        cmd: Buffer
    ){

        this.queue.extend(bytearray(cmd))
        this.queueCount += 1
        // console.log(`Queue count: ${this.queueCount}`)

        if self.autoFlush:
        	self.flush()

    }

    /**
     * Performs a read request after flushing the queue, if needed.
     * 
     * A read request is one which expects a meaningful response.
     * For example, reading data from SPI, or reading a pin's state.
     * 
     * @param cmd Array of bytes to send
     * @param length Expected length of the response from the server
    */
    do_read_request(
        cmd: Buffer,
        length: number
    ){
        this.flush()
        this.sock.send(cmd)
        return this.sock.recv(length)
    }

    /**
     * Sets the state of a single pin.
     * 
     * @param pin The number of the pin to change the state of
     * @param value New value to set for the pin
     */
    set_pin(
        pin: number,
        value: number
    ){
        const cmd = [this.CMD_SET_PIN_SINGLE, pin, value]
        return this.do_write_request(cmd)
    }

    /**
     * Sets the states of multiple pins.
     * 
     * @param pinsAndValues Array of pin:value pairs.
     * eg. [ [16,1], [18,0] ]
     * would set pin 16 to value 1, and pin 18 to value 0.
     */
    set_pins(
        pinsAndValues: Array<Array<number>>
    ){
        
        const numberOfPins = pinsAndValues.length
        
        const cmd = Buffer.alloc(2 + pinsAndValues.length * 2)
        cmd[0] = this.CMD_SET_PIN_MULTI
        cmd[1] = numberOfPins
        
        var i = 2
        pinsAndValues.forEach((pin, value) => {
            cmd[i] = pin
            cmd[i+1] = value
            i += 2
        })
        
        return this.do_write_request(cmd)

    }

    /**
     * Retrieves the value of a single pin.
     * 
     * @param pin Pin to read the value of
     * @return Returns the value of that pin.
     */
    get_pin(
        pin: number
    ){
        
        const numberOfPins = 1
        // console.log(`Get pin ${pin}`)
        const cmd = Buffer([this.CMD_GET_PIN_SINGLE, pin])
        return this.do_read_request(cmd, 1)

    }

    /**
     * Retrieves the value of multiple pins.
     * 
     * @param pins Array of pins to read the values of
     * @return Returns an array of pin values, in order.
     * eg. If you send pins [16,18] and got a response of [0,1]
     * then that means pin 16 has value 0, and pin 18 has value 1.
     */
    get_pins(
        pins: Array<number>
    ){
        
        const numberOfPins = pins.length
        // console.log(`Getting ${numberOfPins} pins`)
        const cmd = Buffer([this.CMD_GET_PIN_MULTI, numberOfPins, ...pins])
        return this.do_read_request(cmd, numberOfPins)

    }

    /**
     * Sends raw byte data to write over SPI.
     * 
     * @param bytedata Array of bytes to write to the SPI device
     */
    write_bytes(
        bytedata: Buffer
    ){
        
        // console.log("Pico write bytes")
        // console.log(`Length: ${bytedata.length}`)
        const lengthBytes = bytedata.length.to_bytes(4, 'big')
        const cmd = Buffer([this.CMD_WRITE_BYTES, ...lengthBytes, ...bytedata])
        return this.do_write_request(cmd)

    }

    /**
     * Tells the Pico server to wait for a defined amount of time
     * before moving onto the next request.
     * 
     * This is useful when sending through multiple commands in a
     * single packet.
     * 
     * For example, let's say your GPIO device requires you to wait
     * for 10ms after setting a pin before writing SPI data.
     * 
     * One way of doing this would be for your client application to
     * send a SET_PIN command, wait 10ms, then send a WRITE_BYTES command.
     * 
     * Another way of doing this would be to send a SET_PIN command, a
     * DELAY command, and a WRITE_BYTES command all in one packet.
     * 
     * The second approach sends 3 commands instead of 2, but it does so
     * in 1 packet instead of 2, making it faster overall due to network
     * latency and packet size constraints.
     * 
     * @param delay_ms Time to wait in milliseconds
     */
    delay(
        delay_ms: number
    ){

        // console.log(`Sending delay of ${delay_ms}`)
        const delayBytes = delay_ms.to_bytes(2, 'big')
        const cmd = Buffer([this.CMD_DELAY, ...delayBytes])
        // console.log(`Sending ${cmd}`)
        return this.do_write_request(cmd)

    }

    /**
     * Waits for a given pin to reach a particular value before
     * continuing execution.
     * 
     * This is useful for waiting until a GPIO device is in a particular
     * state before trying to send it more commands.
     * 
     * eg. Waiting until the BUSY pin is set to 0, indicating that the
     * GPIO device has finished whatever it was doing, before trying to
     * make it do something else.
     * 
     * @param pin Pin to wait on
     * @param value Value to wait for the pin to reach
     * @param delay_ms Milliseconds to wait between pin reads 
     */
    wait_for_pin(
        pin: number,
        value: number,
        delay_ms: number
    ){
        
        // console.log("Sending delay")
        const delayBytes = delay_ms.to_bytes(2, 'big')
        const cmd = Buffer([this.CMD_WAIT_FOR_PIN, pin, value, ...delayBytes])
        return this.do_write_request(cmd)

    }

}
