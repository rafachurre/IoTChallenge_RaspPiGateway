####################
# IMPORT LIBRARIES #
####################
import smbus
import time
import requests
import json
import datetime

####################
# GENERAL SETTINGS #
####################
# Styling for messages in the console
class bMessageStyle:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

################
# CLOUD CONFIG #
################
# Config data needed for the cloud connection
# Endpoint / OAuth Token / Device Id / Message Type Id

# SEND DATA SERVICE CONFIG
#--------------------------
# ~ POST
class oPostData:
    url = "<data_service_endpoint>"
    token = "<token>"
    messageTypeId = "<message_type>"
    headers = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}

# PUSH NOTIFICATIONS SERVICE CONFIG
#-----------------------------------
# ~ GET
class oGetPushMessages:
    url = "<push_service_read_endpoint>"
    token = "<token>"
    headers = {'Authorization': 'Bearer ' + token}

# Seconds wating until next GET request to the Push Notification Service endpoint
getPushNotif_refreshTime = 3

##############
# i2c CONFIG #
##############
# for RPI version 1, use "bus = smbus.SMBus(0)
bus = smbus.SMBus(0)
# This is the address we setup in the Arduino Program
slaveAddress = 0x04
# Seconds after Write() wating to Read() the response
i2c_writeRead_interval = 1

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


############
# FUNCIONS #
############

# ~ i2c communication
def i2c_writeCode(send_code):
    bus.write_byte(slaveAddress, send_code)
    # bus.write_byte_data(slaveAddress, 0, send_code)
    return -1

def i2c_readCode():
    read_code = bus.read_byte(slaveAddress)
    # number = bus.read_byte_data(slaveAddress, 1)
    return read_code

# ~ Cloud communitacion
def cloud_postData(oPostDataParams, oMessageParams):
    """
    class oPostDataParams:
        url
        token
        messageTypeId
        headers

    class oMessageParams:
        status
        timestamp
    """
    payload = {"mode":"sync","messageType":oPostDataParams.messageTypeId,"messages":[{"status": str(oMessageParams["status"]),"timestamp":oMessageParams["timestamp"]}]}
    r = requests.post(oPostDataParams.url, headers=oPostDataParams.headers, data=json.dumps(payload))
    return r.json()

def cloud_getPushMsgs():
    r = requests.get(oGetPushMessages.url, headers=oGetPushMessages.headers)
    return r.json()


# main loop
while True:
    # Get Push Notifications
    pushNotifications = cloud_getPushMsgs()
    print "\nPush Notifications received from Cloud: ", bMessageStyle.OKBLUE, pushNotifications, bMessageStyle.ENDC

    if (len(pushNotifications) > 0):
        index = 0
        while (index < len(pushNotifications)):
            oPushMessage = pushNotifications[index]
            # Encoded           
            oPushMessage_string = json.dumps(oPushMessage)
            # Decoded
            oPushMessage_decoded = json.loads(oPushMessage_string)

            # Send Action Code (i2c)
            iReceivedCode = oPushMessage_decoded["messages"][0]["ActionCode"]
            i2c_writeCode(iReceivedCode)
            print "\nMessage sent (from Master to Slave): ", bMessageStyle.OKGREEN, i2cRequestMessagesDictionary[str(iReceivedCode)], bMessageStyle.ENDC,
            # sleep one second
            time.sleep(i2c_writeRead_interval)

            # Read Response Code (i2c)
            i2c_response_code = i2c_readCode()
            print "\nMessage read (from Slave to Master): ", bMessageStyle.FAIL, i2c_response_code, bMessageStyle.ENDC,
            print

            # Send response to cloud
            currentTime = time.time()
            timestamp = datetime.datetime.fromtimestamp(currentTime).strftime('%Y-%m-%dT%H:%M:%S')
            oMessageParams = {"status": i2c_response_code, "timestamp":timestamp }
            cloud_postData(oPostData, oMessageParams)

            # Update Loop
            index += 1

    time.sleep(getPushNotif_refreshTime)