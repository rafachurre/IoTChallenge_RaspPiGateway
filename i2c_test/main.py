####################
# IMPORT LIBRARIES #
####################
import smbus
import time

##############
# i2c CONFIG #
##############
# for RPI version 1, use "bus = smbus.SMBus(0)
bus = smbus.SMBus(0)
# This is the address we setup in the Arduino Program
slaveAddress = 0x04

# Collection of messages (constants)
SLAVE_STATUS_BOX_OPEN = 1 # The box is open 
SLAVE_STATUS_BOX_CLOSED = 2 # The box is closed 
SLAVE_STATUS_BOX_OPENCLOSED_UNKNOWN = 3 # It is not clear if the box is open or closed (error handling) 
SLAVE_STATUS_BOX_EMPTY = 4 # The box is empty 
SLAVE_STATUS_BOX_FULL = 5 # The box is full 
SLAVE_STATUS_BOX_EMPTYFULL_UNKNOWN = 6 # It is not clear if the box is empty or full (error handling) 
SLAVE_STATUS_LED_BLINKING = 7 # The LED is blinking 
SLAVE_STATUS_LED_OFF = 8 # The LED is off 
SLAVE_STATUS_LED_BLINKINGOFF_UNKNOWN = 9 # It is not clear if the LED is blinking or off (error handling)

SLAVE_STATUS_NO_DATA_REQUEST_RECEIVED_PREVIOUSLY = 50 # Return message when Master reads without writing a DATA_REQUEST message before 
DATA_REQUEST_LAST_CODE_RECEIVED = 51 # Master wants to read() the previous code received. Prepare "to_send" variable for a read event 
DATA_REQUEST_STATUS_OPENCLOSE = 52 # Master wants to read() the open/close status. Prepare "to_send" variable for a read event 
DATA_REQUEST_STATUS_EMPTYFULL = 53 # Master wants to read() the empty/full status. Prepare "to_send" variable for a read event

ACTION_REQUEST_OPEN_BOX = 100 # Master requests to open the box 
ACTION_REQUEST_CLOSE_BOX = 101 # Master requests to close the box 
ACTION_REQUEST_BLINK_LED = 102 # Master requests to blink the LED 
ACTION_REQUEST_TURN_OFF_LED = 103 # Master requests to turn off the LED 
ACTION_REQUEST_SET_KEYPAD_PWD = 104 # Master requests to set a new password. A [0-255] password will be sent in the next write() byte

# Messages dictionaries
#----------------------
i2cSlaveStatusMessagesDictionary = {
        "1": "The box is open",
        "2": "The box is closed",
        "3": "Can't determine if the box is open or closed. Some error may happened",
        "4": "The box is empty",
        "5": "The box is full",
        "6": "Can't determine if the box is empty or full. Some error may happened",
        "7": "The box LED is blinking",
        "8": "The box LED is off",
        "9": "Can't determine if the box LED is blinking or is off. Some error may happened",
        "50": "Slave don't know which data Master wants to read. Send a valid 'REQUEST_DATA' code first"
}
i2cRequestMessagesDictionary = {
        "51": "DATA REQUEST: Slave, please prepare the 'previous_code_received' to be read",
        "52": "DATA REQUEST: Slave, please prepare the 'OpenClose_status' to be read",
        "53": "DATA REQUEST: Slave, please prepare the 'EmptyFull_status' to be read",
        "100": "ACTION: Slave, please open the box",
        "101": "ACTION: Slave, please close the box",
        "102": "ACTION: Slave, please blink the LED",
        "103": "ACTION: Slave, please turn the LED off",
        "104": "ACTION: Slave, please prepare to receive a new password in the next write() request"
}


def writeNumber(send_code):
        bus.write_byte(slaveAddress, send_code)
        # bus.write_byte_data(slaveAddress, 0, send_code)
        return -1

def readNumber():
        read_code = bus.read_byte(slaveAddress)
        # number = bus.read_byte_data(slaveAddress, 1)
        return read_code

while True:
        print "\nAvailable requests: "
        for key in i2cRequestMessagesDictionary:
                print "\n   ", key, ': ', i2cRequestMessagesDictionary[key]
        print "\n"
        send_code = input("Select which request code you want to send: ")
        if not send_code:
                continue

        writeNumber(send_code)
        print "Message sent (from Master to Slave): ", i2cRequestMessagesDictionary[key]
        # sleep one second
        time.sleep(1)

        read_code = readNumber()
        print "Message read (from Slave to Master): ", read_code
        # print "Message read (from Slave to Master): ", i2cSlaveStatusMessagesDictionary[read_code]
        print