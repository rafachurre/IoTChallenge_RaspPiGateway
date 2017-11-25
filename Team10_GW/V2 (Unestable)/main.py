####################
# IMPORT LIBRARIES #
####################
import os
import subprocess
import re
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
debugMode = False

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
class Team10_SlaveAllStatusesMsg:
    url = "<data_service_endpoint>"
    messageTypeId = "<message_type>"
    headers = {'Authorization': 'Bearer ' + deviceInfo.token, 'Content-Type': 'application/json'}
    # Message:  {"messageType":messageTypeId,"messages":[{"timestamp": "", "gwDeviceId": deviceInfo.deviceId, "slaveAddress": sSlaveAddress, "slaveOpenCloseStatus":1,"slaveEmptyFullStatus":2,"slaveLEDStatus":3}]}

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
# This is the collection of address active in the bus
i2c_activeAddresses = []
# This buffer saves the addresses of the devices that provided updates
i2c_slavesWithUpdates = []
# Flag to fire a new scan
i2c_pendingScan = True
scanCounter = 0 # number of cycle waiting before scan
scanFrequency = 10000 # number of mainLoop cycles bere performing a new i2c_scan
# loops waiting until the next read all cycle
i2c_readAll_frequency = 10 # number of "mainLoopSleepTime" cycles before a new readAll
i2c_readAll_counter = 0.1 # Counter of waiting cycles 

# Seconds after Write() wating to Read() the response
i2c_writeRead_interval = 0.1
# Seconds after Write() wating to do the next Write()
i2c_writeWrite_interval = 0.05
# Seconds after Read() wating to do the next Read()
i2c_readRead_interval = 0.01

# Map to monitor the statuses of all slaves
currentSlavesStatuses = {} # currentSlavesStatuses[str(sSlaveAddress)][statusName] WHERE statusName == 'openClose_status' || 'emptyFull_status' || 'LED_status'
openClose_msgsCodes_offset = 0 # Offset to be substracted to convert this status codes to '1', '2', '3' ...
emptyFull_msgsCodes_offset = 3 # Offset to be substracted to convert this status codes to '1', '2', '3' ...
LED_msgsCodes_offset = 6 # Offset to be substracted to convert this status codes to '1', '2', '3' ...

# Collection of messages (constants)
NO_DATA_IN_MESSAGE = -1 # indicates that the involved message has no data associated

SLAVE_NO_BUFFER_DATA = 0 # No data waiting to be read in the slave
SLAVE_STATUS_BOX_OPEN = 1 # The box is open
SLAVE_STATUS_BOX_CLOSED = 2 # The box is closed
SLAVE_STATUS_BOX_OPENCLOSED_UNKNOWN = 3 # It is not clear if the box is open or closed (error handling)
SLAVE_STATUS_BOX_EMPTY = 4 # The box is empty
SLAVE_STATUS_BOX_FULL = 5 # The box is full
SLAVE_STATUS_BOX_EMPTYFULL_UNKNOWN = 6 # It is not clear if the box is empty or full (error handling)
SLAVE_STATUS_LED_BLINKING = 7 # The LED is blinking
SLAVE_STATUS_LED_OFF = 8 # The LED is off
SLAVE_STATUS_LED_BLINKINGOFF_UNKNOWN = 9 # It is not clear if the LED is blinking or off (error handling)

DATA_REQUEST_STATUS_BUFFER_INDEX = 50 # Master wants to know how many items are waiting in the slaveStatusBuffer. Slave prepare the buffer length to be read
DATA_REQUEST_GET_ALL_STATUSES = 51 # Master wants to read() all statuses. Slave, please add them to the buffer to be read in the next read cycle.
DATA_REQUEST_STATUS_OPENCLOSE = 52 # Master wants to read() the open/close status. Prepare "to_send" variable for a read event
DATA_REQUEST_STATUS_EMPTYFULL = 53 # Master wants to read() the empty/full status. Prepare "to_send" variable for a read event
DATA_REQUEST_STATUS_LEDSTATUS = 54 # Master wants to read() the LED blinking/off status. Prepare "to_send" variable for a read event

ACTION_REQUEST_CLEAR_STATUS_BUFFER = 74 # Master requests to reset the slave status buffer
ACTION_REQUEST_OPEN_BOX = 75 # Master requests to open the box
ACTION_REQUEST_CLOSE_BOX = 76 # Master requests to close the box
ACTION_REQUEST_BLINK_LED = 77 # Master requests to blink the LED
ACTION_REQUEST_TURN_OFF_LED = 78 # Master requests to turn off the LED
ACTION_REQUEST_SET_KEYPAD_PWD = 79 # Master requests to set a new password. A [0-255] password will be sent in the next write() byte


############
# GW CODES #
############
GW_STATUS_DEBUG_MODE_ENABLED = 200 # GW DEBUG MODE was enabled
GW_STATUS_DEBUG_MODE_DISABLED = 201 # GW DEBUG MODE was disabled
GW_STATUS_I2C_MESSAGE_SENT = 202 # Message sent via i2c
GW_STATUS_I2C_MESSAGE_READ = 203 # Message read via i2c
GW_STATUS_I2C_POST_DONE = 204 # Data was posted in the Cloud Data Service
GW_STATUS_I2C_SCAN_COMPLETED = 205 # Devices scanned in the i2c bus

GW_ACTION_ENABLE_DEBUG_MODE = 300 # Enables the DebugMode in the GW
GW_ACTION_SCAN_I2C_DEVICES = 301 # Perform a i2c scan

GW_STATUS_GET_PUSH_MSGS_ERROR = 500 # Error Downloading Push messages
GW_STATUS_POST_DATA_ERROR = 501 # Error Postind Data in the cloud
GW_STATUS_I2C_WRITE_ERROR = 502 # Error writing in i2c bus
GW_STATUS_I2C_READ_ERROR = 503 # Error reading in i2c bus

GW_STATUS_I2C_SLAVE_BUFFER_INCONSISTENCY = 600 # Slave status buffer has more than 10 items

# Messages dictionaries
#----------------------
i2cSlaveStatusMessagesDictionary = {
    "0": "No data waiting to be read in the slave",
    "1": "The box is open",
    "2": "The box is closed",
    "3": "Can't determine if the box is open or closed. Some error may happened",
    "4": "The box is empty",
    "5": "The box is full",
    "6": "Can't determine if the box is empty or full. Some error may happened",
    "7": "The box LED is blinking",
    "8": "The box LED is off",
    "9": "Can't determine if the box LED is blinking or is off. Some error may happened"
}
i2cRequestMessagesDictionary = {
    "50": "DATA REQUEST: Slave, please prepare the 'buffer length' to be read",
    "51": "DATA REQUEST: Slave, please prepare add all the statuses to be read",
    "52": "DATA REQUEST: Slave, please prepare the 'OpenClose_status' to be read",
    "53": "DATA REQUEST: Slave, please prepare the 'EmptyFull_status' to be read",
    "54": "DATA REQUEST: Slave, please prepare the 'LED_status' to be read",

    "75": "ACTION: Slave, please open the box",
    "76": "ACTION: Slave, please close the box",
    "77": "ACTION: Slave, please blink the LED",
    "78": "ACTION: Slave, please turn the LED off",
    "79": "ACTION: Slave, please prepare to receive a new password in the next write() request"
}


############
# FUNCIONS #
############

# i2c communication functions #
###############################
def i2c_scanDevices():
    global i2c_activeAddresses
    global currentSlavesStatuses
    i2c_activeAddresses = []
    currentSlavesStatuses = {}
    p = subprocess.Popen(['i2cdetect', '-y','0'],stdout=subprocess.PIPE,)
    #cmdout = str(p.communicate())

    for i in range(0,9):
        l = str(p.stdout.readline())
        for match in re.finditer("[0-9][0-9]:.*[0-9][0-9]", l):
            w = l.split(":")[1].split()
            for address in w:
                if address != "--":
                    hexAddress = "0x" + address
                    i2c_activeAddresses.append(hexAddress)
                    currentSlavesStatuses[str(hexAddress)] = {}

    print_i2cScanDevices(i2c_activeAddresses)

def i2c_forceReadAllSlavesStatuses():
    # Prepare the buffer index in the slave to be read
    if(debugMode):
        print "\nWriting DATA_REQUEST_GET_ALL_STATUSES in all devices"
    for sSlaveAddress in i2c_activeAddresses:
        try:
            i2c_writeCode(sSlaveAddress, DATA_REQUEST_GET_ALL_STATUSES)
            if(debugMode):
                print_i2cMessageSent(sSlaveAddress, DATA_REQUEST_GET_ALL_STATUSES)
        except:
            print_i2c_WriteMsgError(sys.exc_info()[0])

def i2c_writeMessage(sSlaveAddress, iMessageCode, iMessageData):
    i2c_writeCode(int(str(sSlaveAddress), 16), iMessageCode)
    if (iMessageData >= 0):
        # If there is data to send, send it just after sending the code
        time.sleep(i2c_writeWrite_interval)
        i2c_writeCode(int(str(sSlaveAddress), 16), iMessageData)
    return -1

def i2c_writeCode(sSlaveAddress, iMessageCode):
    bus.write_byte(int(str(sSlaveAddress), 16), iMessageCode)
    # bus.write_byte_data(slaveAddress, 0, send_code)
    return -1

def i2c_readCode(sSlaveAddress):
    read_code = bus.read_byte(int(str(sSlaveAddress), 16))
    # number = bus.read_byte_data(slaveAddress, 1)
    return read_code

# Cloud communitacion functions #
#################################
def cloud_Post_SlaveAllStatusesMsg(oMessageParams):
    """
    oMessageParams: {
        slaveAddress
        slaveOpenCloseStatus
        slaveEmptyFullStatus
        slaveLEDStatus
    }

    # payload: {"messageType": messageTypeId,"messages":[{"timestamp": "", "gwDeviceId": deviceInfo.deviceId, "slaveAddress": "", "messageCode": "", "messageData": ""}]}
    """
    currentTime = time.time()
    timestamp = datetime.datetime.fromtimestamp(currentTime).strftime('%Y-%m-%dT%H:%M:%S')

    payload = {"messageType": Team10_SlaveAllStatusesMsg.messageTypeId, "messages":[{"timestamp": timestamp, "gwDeviceId": deviceInfo.deviceId, "slaveAddress": oMessageParams["slaveAddress"], "slaveOpenCloseStatus": oMessageParams["slaveOpenCloseStatus"], "slaveEmptyFullStatus": oMessageParams["slaveEmptyFullStatus"], "slaveLEDStatus": oMessageParams["slaveLEDStatus"]}]}
    r = requests.post(Team10_SlaveAllStatusesMsg.url, headers=Team10_SlaveAllStatusesMsg.headers, data=json.dumps(payload))
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
def print_i2cScanDevices(devices):
    gwStatusMessage = "i2c SCAN: ", "[", ','.join(devices), "]"
    oGW_MessageParams = {"gwStatusCode": GW_STATUS_I2C_SCAN_COMPLETED, "gwStatusMessage": gwStatusMessage}
    cloud_Post_GWStatus(oGW_MessageParams)
    if(debugMode):
        print "Scan completed. Detected devices: "
        print "[", ','.join(devices), "]"

def print_i2cMessageSent(sSlaveAddress, iMessageCode):
    sConsoleMessage = ""
    sLogMessage = ""
    if str(iMessageCode) in i2cRequestMessagesDictionary:
        sConsoleMessage = "\nMessage sent (from Master to Slave): ", bMessageStyle.OKGREEN, i2cRequestMessagesDictionary[str(iMessageCode)], "(SlaveAddress: ", sSlaveAddress, ")", bMessageStyle.ENDC
        sLogMessage = "\nMessage sent (from Master to Slave): ", i2cRequestMessagesDictionary[str(iMessageCode)], "(SlaveAddress: ", sSlaveAddress, ")"
    else:
        sConsoleMessage = "\nMessage sent (from Master to Slave): ", bMessageStyle.OKGREEN, str(iMessageCode), "(SlaveAddress: ", sSlaveAddress, ")", bMessageStyle.ENDC
        sLogMessage = "\nMessage sent (from Master to Slave): ", i2cRequestMessagesDictionary[str(iMessageCode)], "(SlaveAddress: ", sSlaveAddress, ")"

    print "".join(sConsoleMessage)

    gwStatusMessage = "DEBUGGER: ", sLogMessage
    oGW_MessageParams = {"gwStatusCode": GW_STATUS_I2C_MESSAGE_SENT, "gwStatusMessage": gwStatusMessage}
    cloud_Post_GWStatus(oGW_MessageParams)

def print_i2cMessageReceived(sSlaveAddress, iResponseCode):
    sConsoleMessage = ""
    sLogMessage = ""
    if str(iResponseCode) in i2cSlaveStatusMessagesDictionary:
        sConsoleMessage = "\nMessage read (from Slave ", sSlaveAddress, ") ", bMessageStyle.FAIL, i2cSlaveStatusMessagesDictionary[str(iResponseCode)], bMessageStyle.ENDC
        sLogMessage = "\nMessage read (from Slave ", sSlaveAddress, ") ", i2cSlaveStatusMessagesDictionary[str(iResponseCode)]
    else:
        sConsoleMessage = "\nMessage read (from Slave ", sSlaveAddress, ") ", bMessageStyle.FAIL, str(iResponseCode), bMessageStyle.ENDC
        sLogMessage = "\nMessage read (from Slave ", sSlaveAddress, ") ", str(iResponseCode)
    
    print "".join(sConsoleMessage)

    gwStatusMessage = "DEBUGGER: ", sLogMessage
    oMessageParams = {"gwStatusCode": GW_STATUS_I2C_MESSAGE_READ, "gwStatusMessage": gwStatusMessage}
    cloud_Post_GWStatus(oMessageParams)

def print_i2cBufferLenghtReceived(sSlaveAddress, iBufferLength):
    sConsoleMessage = "\nMessage read (from Slave: ", sSlaveAddress, ") ", bMessageStyle.BOLD, str(iBufferLength), bMessageStyle.ENDC
    sLogMessage = "\nMessage read (from Slave: ", sSlaveAddress, ") ", str(iBufferLength)
    
    print "".join(sConsoleMessage)

    gwStatusMessage = "DEBUGGER: ", sLogMessage
    oMessageParams = {"gwStatusCode": GW_STATUS_I2C_MESSAGE_READ, "gwStatusMessage": gwStatusMessage}
    cloud_Post_GWStatus(oMessageParams)

def print_cloudPostDone(response):
    print "POST RESPONSE: ", bMessageStyle.OKGREEN, response, bMessageStyle.ENDC
    gwStatusMessage = "POST Response: ", response
    oMessageParams = {"gwStatusCode": GW_STATUS_I2C_POST_DONE, "gwStatusMessage": gwStatusMessage}
    cloud_Post_GWStatus(oMessageParams)

def print_GetPushMsgsError(error):
    print bMessageStyle.FAIL, "ERROR GETTING PUSH MESSAGES: ", error, bMessageStyle.ENDC
    gwStatusMessage = "ERROR GETTING PUSH MESSAGES: ", error
    oMessageParams = {"gwStatusCode": GW_STATUS_GET_PUSH_MSGS_ERROR, "gwStatusMessage": gwStatusMessage}
    cloud_Post_GWStatus(oMessageParams)

def print_postDataToCloud(error):
    print bMessageStyle.FAIL, "ERROR POSTING DATA TO CLOUD: ", error, bMessageStyle.ENDC
    gwStatusMessage = "ERROR POSTING DATA TO CLOUD: ", error
    oMessageParams = {"gwStatusCode": GW_STATUS_POST_DATA_ERROR, "gwStatusMessage": gwStatusMessage}
    cloud_Post_GWStatus(oMessageParams)

def print_i2c_WriteMsgError(error):
    print bMessageStyle.FAIL, "ERROR WRITING IN I2C BUS: ", error, bMessageStyle.ENDC
    gwStatusMessage = "ERROR WRITING IN I2C BUS: ", error
    oMessageParams = {"gwStatusCode": GW_STATUS_I2C_WRITE_ERROR, "gwStatusMessage": gwStatusMessage}
    cloud_Post_GWStatus(oMessageParams)

def print_i2c_ReadMsgError(error):
    print bMessageStyle.FAIL, "ERROR READING FROM I2C BUS: ", error, bMessageStyle.ENDC
    gwStatusMessage = "ERROR READING FROM I2C BUS: ", error
    oMessageParams = {"gwStatusCode": GW_STATUS_I2C_READ_ERROR, "gwStatusMessage": gwStatusMessage}
    cloud_Post_GWStatus(oMessageParams)

def print_i2c_SlaveBufferLength_Inconsistency(sSlaveAddress, iBufferLength):
    print bMessageStyle.FAIL, "Inconsistency detected in slave: ", sSlaveAddress, " --> status_buffer_length=", slaveBufferLength, bMessageStyle.ENDC
    gwStatusMessage = "Inconsistency detected in slave: ", sSlaveAddress, " --> status_buffer_length=", slaveBufferLength
    oMessageParams = {"gwStatusCode": GW_STATUS_I2C_SLAVE_BUFFER_INCONSISTENCY, "gwStatusMessage": gwStatusMessage}
    cloud_Post_GWStatus(oMessageParams)


# Runtime functions #
#####################

# Execute the action received for the Master
def performMasterAction(iMessageCode, iMessageData):
    if (iMessageCode == GW_ACTION_ENABLE_DEBUG_MODE):
        sGwStatusMessage = ""
        iGwStatusCode = ""
        if(iMessageData == 1):
            global debugMode
            debugMode = True
            sGwStatusMessage = "Debug mode ENABLED"
            iGwStatusCode = GW_STATUS_DEBUG_MODE_ENABLED
        else: 
            global debugMode
            debugMode = False
            sGwStatusMessage = "Debug mode DISABLED"
            iGwStatusCode = GW_STATUS_DEBUG_MODE_DISABLED
        oMessageParams = {"gwStatusCode": iGwStatusCode, "gwStatusMessage": sGwStatusMessage}
        cloud_Post_GWStatus(oMessageParams)

    if (iMessageCode == GW_ACTION_SCAN_I2C_DEVICES):
        global i2c_pendingScan
        i2c_pendingScan = True

# Get Push Notifications
def downloadPushMessages():
    try:
        pushNotifications = cloud_Get_PushMsgs()
    except:
        print_GetPushMsgsError(sys.exc_info()[0])
    global pushMessagesBuffer
    pushMessagesBuffer += pushNotifications
    if(debugMode):
        print "\nPush Notifications received from Cloud: ", bMessageStyle.OKBLUE, pushNotifications, bMessageStyle.ENDC

# If one slave have updates, add its address to the buffer to send the data to the cloud later
def updateSlaveWithUpdatesBuffer(sSlaveAddress):
    global i2c_slavesWithUpdates
    i2c_slavesWithUpdates.append(sSlaveAddress)

# update currentSlavesStatuses, currentSlavesStatuses[str(sSlaveAddress)][statusName] WHERE statusName == 'openClose_status' or 'emptyFull_status' or 'LED_status'
def updateSlaveStatus(sSlaveAddress, iStatusCode):
    global currentSlavesStatuses
    if(iStatusCode == SLAVE_STATUS_BOX_OPEN or iStatusCode == SLAVE_STATUS_BOX_CLOSED or iStatusCode == SLAVE_STATUS_BOX_OPENCLOSED_UNKNOWN):
        if sSlaveAddress not in currentSlavesStatuses:
            currentSlavesStatuses[str(sSlaveAddress)] = {}
        openClose_status = iStatusCode - openClose_msgsCodes_offset
        currentSlavesStatuses[str(sSlaveAddress)]['openClose_status'] = openClose_status

    elif(iStatusCode == SLAVE_STATUS_BOX_EMPTY or iStatusCode == SLAVE_STATUS_BOX_FULL or iStatusCode == SLAVE_STATUS_BOX_EMPTYFULL_UNKNOWN):
        if sSlaveAddress not in currentSlavesStatuses:
            currentSlavesStatuses[str(sSlaveAddress)] = {}
        emptyFull_status = iStatusCode - emptyFull_msgsCodes_offset
        currentSlavesStatuses[str(sSlaveAddress)]['emptyFull_status'] = emptyFull_status
        
    elif(iStatusCode == SLAVE_STATUS_LED_BLINKING or iStatusCode == SLAVE_STATUS_LED_OFF or iStatusCode == SLAVE_STATUS_LED_BLINKINGOFF_UNKNOWN):
        if sSlaveAddress not in currentSlavesStatuses:
            currentSlavesStatuses[str(sSlaveAddress)] = {}
        LED_status = iStatusCode - LED_msgsCodes_offset
        currentSlavesStatuses[str(sSlaveAddress)]['LED_status'] = LED_status
# If there are status updates pending to be posted in the cloud, send them
def uploadSlavesStatusUpdates():
    if (len(i2c_slavesWithUpdates) > 0):
        for i in range(0, len(i2c_slavesWithUpdates)):
            sSlaveAddress = i2c_slavesWithUpdates.pop()
            oMessageParams = { "slaveAddress": sSlaveAddress , "slaveOpenCloseStatus": currentSlavesStatuses[str(sSlaveAddress)]['openClose_status'], "slaveEmptyFullStatus": currentSlavesStatuses[str(sSlaveAddress)]['emptyFull_status'], "slaveLEDStatus": currentSlavesStatuses[str(sSlaveAddress)]['LED_status'] }
            try:
                response = cloud_Post_SlaveAllStatusesMsg(oMessageParams)
                if(debugMode):
                    print_cloudPostDone(response)
            except:
                print_postDataToCloud(sys.exc_info()[0])

# Read data in those devices with pending data waing in the buffer
def readAvalableDevices():
    if(debugMode):
        print "\nReading all available devices: ", str(i2c_activeAddresses)
    if (len(i2c_activeAddresses) > 0):
        for sSlaveAddress in i2c_activeAddresses:
            # Prepare the buffer index in the slave to be read
            if(debugMode):
                print "\nWriting DATA_REQUEST_STATUS_BUFFER_INDEX in device: ", sSlaveAddress
            try:
                i2c_writeMessage(sSlaveAddress, DATA_REQUEST_STATUS_BUFFER_INDEX, NO_DATA_IN_MESSAGE)
                if(debugMode):
                    print_i2cMessageSent(sSlaveAddress, DATA_REQUEST_STATUS_BUFFER_INDEX)
            except:
                print_i2c_WriteMsgError(sys.exc_info()[0])
            
            # sleep i2c_writeRead_interval seconds
            time.sleep(i2c_writeRead_interval)

            # Read Response Code (i2c)
            slaveBufferLength = 0
            if(debugMode):
                print "\nReading Status_Buffer_Length from slave: ", sSlaveAddress
            try:
                slaveBufferLength = i2c_readCode(sSlaveAddress)
                if(debugMode):
                    print_i2cBufferLenghtReceived(sSlaveAddress, slaveBufferLength)
            except:
                print_i2c_ReadMsgError(sys.exc_info()[0])

            # if slaveBuffer is greater than 10, there is an inconsistency. Clear the slave buffer and read all statuses again
            if(slaveBufferLength > 10):
                if(debugMode):
                    print_i2c_SlaveBufferLength_Inconsistency(sSlaveAddress, iBufferLength)
                # Reset Slave buffer
                try:
                    i2c_writeMessage(sSlaveAddress, ACTION_REQUEST_CLEAR_STATUS_BUFFER, NO_DATA_IN_MESSAGE)
                    if(debugMode):
                        print_i2cMessageSent(sSlaveAddress, ACTION_REQUEST_CLEAR_STATUS_BUFFER)
                except:
                    print_i2c_WriteMsgError(sys.exc_info()[0])

            # If slaveBuffer is lower than 10 and greater than 0, then read the
            elif(slaveBufferLength > 0):
                if(debugMode):
                    print "\nReading ", slaveBufferLength, " pending items from slave: ", sSlaveAddress
                # Add the slave address to the buffer
                updateSlaveWithUpdatesBuffer(sSlaveAddress)
                # Read all the pending status codes and update the list
                for i in range(0, slaveBufferLength):
                    time.sleep(i2c_readRead_interval)
                    i2c_received_code = 0
                    try:
                        i2c_received_code = i2c_readCode(sSlaveAddress)
                        if(debugMode):
                            print_i2cMessageReceived(sSlaveAddress, i2c_received_code)
                    except:
                        print_i2c_ReadMsgError(sys.exc_info()[0])
                    
                    if(i2c_received_code != SLAVE_NO_BUFFER_DATA):
                        updateSlaveStatus(sSlaveAddress, i2c_received_code)
                    # Sleep i2c_readRead_interval seconds
                    time.sleep(i2c_readRead_interval)

def proccessPendingPushMessages():
    if (len(pushMessagesBuffer) > 0):
        for i in range(0, slaveBufferLength):
            oPushMessage = pushMessagesBuffer.pop()
            # Encoded           
            oPushMessage_string = json.dumps(oPushMessage)
            # Decoded
            oPushMessage_decoded = json.loads(oPushMessage_string)

            # Proccess push message
            sSlaveAddress = oPushMessage_decoded["messages"][0]["slaveAddress"]
            iMessageCode = oPushMessage_decoded["messages"][0]["actionCode"]
            iMessageData = oPushMessage_decoded["messages"][0]["actionData"]
            if (oPushMessage_decoded["messages"][0]["slaveAddress"] == "Master"):
                performMasterAction(iMessageCode, iMessageData)
            else: 
                # Write Code (i2c)
                try:
                    i2c_writeMessage(sSlaveAddress, iMessageCode, iMessageData)
                    if(debugMode):
                        print_i2cMessageSent(sSlaveAddress, iMessageCode)
                except:
                    print_i2c_WriteMsgError(sys.exc_info()[0])
            
            # sleep i2c_writeWrite_interval seconds
            time.sleep(i2c_writeWrite_interval)

#############
# MAIN LOOP #
#############
while True:

    time.sleep(mainLoopSleepTime)

    # Download push messages #
    ##########################
    # If there are items in the buffer, we will spend "i2c_writeRead_interval" seconds to process each message, so we need to check for new post messages, just afterwards
    # Otherwise, check if there are messages just after getPushNotif_refreshFrequency cycles
    if(len(pushMessagesBuffer) > 0 or getPushNotif_cyclesCounter >= getPushNotif_refreshFrequency):
        # Update counter
        getPushNotif_cyclesCounter = 0
        downloadPushMessages()
    else:
        # Update counter
        getPushNotif_cyclesCounter += 1

    # Check is there is a pending device scan #
    ###########################################
    if(i2c_pendingScan):
        i2c_pendingScan = False
        i2c_scanDevices()
        i2c_forceReadAllSlavesStatuses()


    # Read Slaves statuses #
    ########################
    if (i2c_readAll_counter >= i2c_readAll_frequency):
        # Update counter
        i2c_readAll_counter = 0
        # Read devices available in the bus
        readAvalableDevices()
    else:
        # Update counter
        i2c_readAll_counter += 1

    # POST Slaves statuses to the cloud #
    #####################################
    # Upload pending status updates
    uploadSlavesStatusUpdates()

    # Process pending push messsages #
    ##################################
    # Upload pending status updates
    proccessPendingPushMessages()

    # Update i2c_scan counter #
    ###########################
    if (len(i2c_activeAddresses) <= 0 and scanCounter < scanFrequency):
        scanCounter += 1
    elif (len(i2c_activeAddresses) <= 0 ):
        scanCounter = 0
        i2c_pendingScan = True