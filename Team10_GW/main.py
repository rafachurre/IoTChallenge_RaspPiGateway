####################
# IMPORT LIBRARIES #
####################
import sys
import smbus
import time
import requests
import json
import datetime

####################
# GENERAL SETTINGS #
####################
# main loop sleep
mainLoopSleepTime = 0.05

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

# Seconds wating until next GET request to the Push Notification Service endpoint
getPushNotif_cyclesCounter = 0 # Cycles counter
getPushNotif_refreshFrequency = 10 # number if cycles before sending a GET request to the Post Messages Service

# SEND DATA SERVICE CONFIG
#--------------------------

# ~ DEVICE
class deviceInfo:
    deviceId= "<DeviceID>"
    token = "<token>"

# ~ POST Messages
class Team10_DevicePostMsg:
    url = "<data_service_endpoint>"
    messageTypeId = "<message_type>"
    headers = {'Authorization': 'Bearer ' + deviceInfo.token, 'Content-Type': 'application/json'}
    # Message: {"messageType": messageTypeId,"messages":[{"timestamp": "", "gwDeviceId": deviceInfo.deviceId, "slaveAddress": "", "messageCode": "", "messageData": ""}]}

class Team10_GWStatus:
    url = "<data_service_endpoint>"
    messageTypeId = "<message_type>"
    headers = {'Authorization': 'Bearer ' + deviceInfo.token, 'Content-Type': 'application/json'}
    # Message: {"messageType": messageTypeId,"messages":[{"timestamp": "", "gwDeviceId": deviceInfo.deviceId, "gwStatusCode": "", "gwStatusMessage": ""}]}

class Team10_SlaveStatus:
    url = "<data_service_endpoint>"
    messageTypeId = "<message_type>"
    headers = {'Authorization': 'Bearer ' + deviceInfo.token, 'Content-Type': 'application/json'}
    # Message: {"messageType": messageTypeId,"messages":[{"timestamp": "", "gwDeviceId": deviceInfo.deviceId, "slaveAddress": "", "slaveStatusCode": ""}]}
    
# ~ GET PUSH Messages
pushMessagesBuffer = []
class Team10_PushToGW:
    url = "<push_service_read_endpoint>"
    headers = {'Authorization': 'Bearer ' + deviceInfo.token}


##############
# i2c CONFIG #
##############
# for RPI version 1, use "bus = smbus.SMBus(0)
bus = smbus.SMBus(0)
# This is the address we setup in the Arduino Program
# slaveAddress = 0x04
# Seconds after Write() wating to Read() the response
i2c_writeRead_interval = 0.5
i2c_writeWrite_interval = 0.05

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


###################
# GW STATUS CODES #
###################
GW_STATUS_DEBUG_MODE_ENABLED = 200 # GW DEBUG MODE was enabled
GW_STATUS_DEBUG_MODE_DISABLED = 201 # GW DEBUG MODE was disabled
GW_STATUS_I2C_MESSAGE_SENT = 202 # Message sent via i2c
GW_STATUS_I2C_MESSAGE_READ = 203 # Message read via i2c
GW_STATUS_I2C_POST_DONE = 204 # Data was posted in the Cloud Data Service

GW_STATUS_I2C_POST_ERROR = 500 # Execution error


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

# Execute the action received for the Master
def performMasterAction(iMessageCode, iMessageData):
    if (iMessageCode == 200):
        sGwStatusMessage = ""
        iGwStatusCode = ""
        if(iMessageData == 1):
            debugMode = True
            sGwStatusMessage = "Debug mode ENABLED"
            iGwStatusCode = GW_STATUS_DEBUG_MODE_ENABLED
        else: 
            debugMode = False
            sGwStatusMessage = "Debug mode DISABLED"
            iGwStatusCode = GW_STATUS_DEBUG_MODE_DISABLED
        oMessageParams = {"gwStatusCode": iGwStatusCode, "gwStatusMessage": sGwStatusMessage}
        cloud_Post_GWStatus(oMessageParams)

# ~ i2c communication
def i2c_writeMessage(sSlaveAddress, iMessageCode, iMessageData):
    i2c_writeCode(sSlaveAddress, iMessageCode)
    if iMessageData is not None:
        # If there is data to send, send it just after sending the code
        time.sleep(i2c_writeWrite_interval)
        i2c_writeCode(sSlaveAddress, iMessageData)
    return -1

def i2c_writeCode(sSlaveAddress, iMessageCode):
    bus.write_byte(sSlaveAddress, iMessageCode)
    # bus.write_byte_data(slaveAddress, 0, send_code)
    return -1

def i2c_readCode():
    read_code = bus.read_byte(slaveAddress)
    # number = bus.read_byte_data(slaveAddress, 1)
    return read_code

# ~ Cloud communitacion
def cloud_Post_DevicePostMsg(oMessageParams):
    """
    oMessageParams: {
        slaveAddress
        messageCode
        messageData
    }

    # payload: {"messageType": messageTypeId,"messages":[{"timestamp": "", "gwDeviceId": deviceInfo.deviceId, "slaveAddress": "", "messageCode": "", "messageData": ""}]}
    """
    currentTime = time.time()
    timestamp = datetime.datetime.fromtimestamp(currentTime).strftime('%Y-%m-%dT%H:%M:%S')

    payload = {"messageType": Team10_DevicePostMsg.messageTypeId, "messages":[{"timestamp": timestamp, "gwDeviceId": deviceInfo.deviceId, "slaveAddress": oMessageParams["slaveAddress"], "messageCode": oMessageParams["messageCode"], "messageData": oMessageParams["messageData"]}]}
    r = requests.post(Team10_DevicePostMsg.url, headers=Team10_DevicePostMsg.headers, data=json.dumps(payload))
    return r.json()

def cloud_Post_GWStatus(oMessageParams):
    """
    oMessageParams: {
        gwStatusCode
        gwStatusMessage
    }

    # payload: {"messageType": messageTypeId,"messages":[{"timestamp": "", "gwDeviceId": deviceInfo.deviceId, "gwStatusCode": "", "gwStatusMessage": ""}]}
    """
    currentTime = time.time()
    timestamp = datetime.datetime.fromtimestamp(currentTime).strftime('%Y-%m-%dT%H:%M:%S')

    payload = {"messageType": Team10_GWStatus.messageTypeId, "messages":[{"timestamp": timestamp, "gwDeviceId": deviceInfo.deviceId, "gwStatusCode": oMessageParams["gwStatusCode"], "gwStatusMessage": oMessageParams["gwStatusMessage"]}]}
    r = requests.post(Team10_GWStatus.url, headers=Team10_GWStatus.headers, data=json.dumps(payload))
    return r.json()

def cloud_Post_SlaveStatus(oMessageParams):
    """
    oMessageParams: {
        slaveAddress
        slaveStatusCode
    }

    # payload: {"messageType": messageTypeId,"messages":[{"timestamp": "", "gwDeviceId": deviceInfo.deviceId, "slaveAddress": "", "slaveStatusCode": ""}]}
    """
    currentTime = time.time()
    timestamp = datetime.datetime.fromtimestamp(currentTime).strftime('%Y-%m-%dT%H:%M:%S')

    payload = {"messageType": Team10_SlaveStatus.messageTypeId, "messages":[{"timestamp": timestamp, "gwDeviceId": deviceInfo.deviceId, "slaveAddress": oMessageParams["slaveAddress"], "slaveStatusCode": oMessageParams["slaveStatusCode"]}]}
    r = requests.post(Team10_SlaveStatus.url, headers=Team10_SlaveStatus.headers, data=json.dumps(payload))
    return r.json()

def cloud_Get_PushMsgs():
    """
    # payload: ["messages": [{"timestamp": "", "gwDeviceId": "", "slaveAddress": "", "messageCode": "", "messageData": ""}]}
    """
    r = requests.get(Team10_PushToGW.url, headers=Team10_PushToGW.headers)
    return r.json()

# Console log functions #
#########################
def print_i2cMessageSent(sSlaveAddress, iMessageCode):
    sConsoleMessage = ""
    sLogMessage = ""
    if str(iMessageCode) in i2cRequestMessagesDictionary:
        sConsoleMessage = "\nMessage sent (from Master to Slave): ", bMessageStyle.OKGREEN, i2cRequestMessagesDictionary[str(iMessageCode)], bMessageStyle.ENDC, "(SlaveAddress: ", sSlaveAddress, ")"
        sLogMessage = "\nMessage sent (from Master to Slave): ", i2cRequestMessagesDictionary[str(iMessageCode)], "(SlaveAddress: ", sSlaveAddress, ")"
    else:
        sConsoleMessage = "\nMessage sent (from Master to Slave): ", bMessageStyle.OKGREEN, str(iMessageCode), bMessageStyle.ENDC, "(SlaveAddress: ", sSlaveAddress, ")"
        sLogMessage = "\nMessage sent (from Master to Slave): ", i2cRequestMessagesDictionary[str(iMessageCode)], "(SlaveAddress: ", sSlaveAddress, ")"

    print sConsoleMessage

    gwStatusMessage = "DEBUGGER: ", sLogMessage
    oGW_MessageParams = {"gwStatusCode": GW_STATUS_I2C_MESSAGE_SENT, "gwStatusMessage": gwStatusMessage}
    cloud_Post_GWStatus(oGW_MessageParams)

def print_i2cMessageReceived(sSlaveAddress, iResponseCode):
    sConsoleMessage = ""
    sLogMessage = ""
    if str(iResponseCode) in i2cSlaveStatusMessagesDictionary:
        sConsoleMessage = "\nMessage read (from Slave to Master): ", bMessageStyle.FAIL, i2cSlaveStatusMessagesDictionary[str(iResponseCode)], bMessageStyle.ENDC
        sLogMessage = "\nMessage read (from Slave to Master): ", i2cSlaveStatusMessagesDictionary[str(iResponseCode)]
    else:
        sConsoleMessage = "\nMessage sent (from Master to Slave): ", bMessageStyle.FAIL, str(iResponseCode), bMessageStyle.ENDC
        sLogMessage = "\nMessage sent (from Master to Slave): ", str(iResponseCode)
    
    print sConsoleMessage

    gwStatusMessage = "DEBUGGER: ", sLogMessage
    oMessageParams = {"gwStatusCode": GW_STATUS_I2C_MESSAGE_READ, "gwStatusMessage": gwStatusMessage}
    cloud_Post_GWStatus(oMessageParams)

def print_cloudPostDone(response):
    print "POST RESPONSE: ", bMessageStyle.OKGREEN, response, bMessageStyle.ENDC
    gwStatusMessage = "POST Response: ", response
    oMessageParams = {"gwStatusCode": GW_STATUS_I2C_POST_DONE, "gwStatusMessage": gwStatusMessage}
    cloud_Post_GWStatus(oMessageParams)

def print_executionError(error):
    print "EXECUTION ERROR: ", bMessageStyle.FAIL, error, bMessageStyle.ENDC
    gwStatusMessage = "EXECUTION ERROR: ", error
    oMessageParams = {"gwStatusCode": GW_STATUS_I2C_POST_ERROR, "gwStatusMessage": gwStatusMessage}
    cloud_Post_GWStatus(oMessageParams)


# main loop #
#############
while True:
    time.sleep(mainLoopSleepTime)

    # Read push messages #
    ######################
    # If there are items in the buffer, we will spend 0.5s to process each message, so we need to check for new post messages, just afterwards
    # Otherwise, check if there are messages just after getPushNotif_refreshFrequency cycles
    if(len(pushMessagesBuffer) > 0 or getPushNotif_cyclesCounter >= getPushNotif_refreshFrequency):
        # Update counter
        getPushNotif_cyclesCounter = 0
        # Get Push Notifications
        try:
            pushNotifications = cloud_Get_PushMsgs()
        except:
            print_executionError(sys.exc_info()[0])
        pushMessagesBuffer += pushNotifications
        if(debugMode):
            print "\nPush Notifications received from Cloud: ", bMessageStyle.OKBLUE, pushNotifications, bMessageStyle.ENDC
    else:
        # Update counter
        getPushNotif_cyclesCounter += 1

    # Process pending push messsages #
    ##################################
    if (len(pushMessagesBuffer) > 0):
        oPushMessage = pushMessagesBuffer.pop([0])
        # Encoded           
        oPushMessage_string = json.dumps(oPushMessage)
        # Decoded
        oPushMessage_decoded = json.loads(oPushMessage_string)

        # Proccess push message
        sSlaveAddress = oPushMessage_decoded["messages"][0]["slaveAddress"]
        iMessageCode = oPushMessage_decoded["messages"][0]["messageCode"]
        iMessageData = oPushMessage_decoded["messages"][0]["messageData"]
        if (oPushMessage_decoded["messages"][0]["slaveAddress"] == "Master"):
            performMasterAction(iMessageCode, iMessageData)
        else: 
            i2c_writeMessage(sSlaveAddress, iMessageCode, iMessageData)
            if(debugMode):
                print_i2cMessageSent(iMessageCode)
            
            # sleep i2c_writeRead_interval seconds
            time.sleep(i2c_writeRead_interval)

            # Read Response Code (i2c)
            i2c_response_code = i2c_readCode(sSlaveAddress)
            if(debugMode):
                print_i2cMessageReceived(i2c_response_code)

            # Send response to cloud
            oMessageParams = {"slaveAddress": slaveAddress, "messageCode": i2c_response_code, "messageData": 0 }
            response = cloud_Post_DevicePostMsg(oMessageParams)
            if(debugMode):
                print_cloudPostDone(response)

