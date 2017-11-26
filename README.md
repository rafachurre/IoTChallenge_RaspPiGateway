# IoTChallenge_RaspPiGateway
This repository saves the code for the Raspberry Pi Gateway in the "NoFrontiers" project for the 2017 IoT Challenge

### What is this?
This GW python script communicates, via i2c, a Raspberry Pi with any Slave available in the bus. 
It scans the bus first, to know which are the addresses available. The talks to all the slaves periodically.
The data read from each slave is sent to the cloud via HTTP POST messages.

The GW also retrieves push messages polling an HTTP service in the cloud. 
Each push message can send a message to one slave in the i2c bus or execute certain functions in the GW

The GW has also a Debug_Mode that can be activated via Push message.
When Debug_Mode is active, the GW posts the execution logs to the cloud via HTTP POST messages.

### Messages
The messages this GW can understand are:
```
################
# I2C Messages #
################
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


###############
# GW MESSAGES #
###############
GW_STATUS_DEBUG_MODE_ENABLED = 200 # GW DEBUG MODE was enabled
GW_STATUS_DEBUG_MODE_DISABLED = 201 # GW DEBUG MODE was disabled
GW_STATUS_I2C_MESSAGE_SENT = 202 # Message sent via i2c
GW_STATUS_I2C_MESSAGE_READ = 203 # Message read via i2c
GW_STATUS_I2C_POST_DONE = 204 # Data was posted in the Cloud Data Service
GW_STATUS_I2C_SCAN_COMPLETED = 205 # Devices scanned in the i2c bus

# To execute this actions, the "sSlaveAddress" should be "Master"
GW_ACTION_ENABLE_DEBUG_MODE = 300 # if "sMessageData"=1 Enables the DebugMode in the GW / otherwhise it disables DebugMode
GW_ACTION_SCAN_I2C_DEVICES = 301 # Perform a i2c scan

GW_STATUS_GET_PUSH_MSGS_ERROR = 500 # Error Downloading Push messages
GW_STATUS_POST_DATA_ERROR = 501 # Error Postind Data in the cloud
GW_STATUS_I2C_WRITE_ERROR = 502 # Error writing in i2c bus
GW_STATUS_I2C_READ_ERROR = 503 # Error reading in i2c bus

GW_STATUS_I2C_SLAVE_BUFFER_INCONSISTENCY = 600 # Slave status buffer has more than 10 items
```


# HOW TO INSTALL

1. Install a OS for your Raspberry Pi. Rasbian is the recommended one: [Follow this tutorial](https://www.raspberrypi.org/documentation/installation/installing-images/README.md)
2. Update the OS
```
> sudo apt-get update
> sudo apt-get upgrade
```
3. Install Git if you don't have it yet
```
> sudo apt-get install git
> sudo git config --global user.email "you@example.com"
> sudo git config --global user.name "Your Name"
```
4. Install Python-pip and other add-ons
```
> cd /home/pi/
> sudo mkdir pip
> cd /home/pi/pip
> sudo apt-get install python-pip
> sudo pip install --upgrade pip
> sudo pip install setuptools
> sudo pip install pipenv
> sudo pipenv install requests
```
5. Enable i2c
   The easiest way (in my opinion) is through the raspi-config menu
```
> sudo raspi-config
```
   Select the option ***"Interfacing Options" > I2C*** and follow the steps</br>

   **Manual Option**

   Check out [this link](https://learn.adafruit.com/adafruits-raspberry-pi-lesson-4-gpio-setup/configuring-i2c) for other options

6. Install i2c-tools and python-smbus
```
> sudo apt-get install i2c-tools
> sudo adduser pi i2c
> sudo apt-get install python-smbus
```
7. Clone IoTChallenge_GW script
```
> cd /home
> sudo git clone https://github.com/rafachurre/IoTChallenge_RaspPiGateway.git
> cd /home/IoTChallenge_RaspPiGateway/Team10_GW/Last_Stable_Version/
```

8. Modify "deviceInfo" class: Set the "deviceId" and the OAuth Token for enabling the cloud interaction.
```
sudo nano main.py
```

    a) set deviceId instead of "<DeviceID>"

    b) set OAuth Token for this device instead of "<token>"

    c) Save and exit the editor

9. Make the file executable
```
> cd /home/IoTChallenge_RaspPiGateway/Team10_GW/Last_Stable_Version/
> sudo chmod +x main.py
```

10. Edit "rc.local" file to execute the script when booting the OS
```
> sudo nano /etc/rc.local
```

   add the line: 

 > python /home/IoTChallenge_RaspPiGateway/Team10_GW/Last_Stable_Version/main.py
 
   It should be something like the following code:
 
```
#!/bin/sh -e
#
# rc.local
#
# This script is executed at the end of each multiuser runlevel.
# Make sure that the script will "exit 0" on success or any other
# value on error.
#
# In order to enable or disable this script just change the execution
# bits.
#
# By default this script does nothing.

# Print the IP address
_IP=$(hostname -I) || true
if [ "$_IP" ]; then
  printf "My IP address is %s\n" "$_IP"
fi

python /home/IoTChallenge_RaspPiGateway/Team10_GW/Last_Stable_Version/main.py

exit 0
```



# IoTChallenge schematics

Setting this with the [IoTChallenge_ArduinoBoxSlaves](https://github.com/rafachurre/IoTChallenge_ArduinoBoxSlaves)

.

![schematics picture](https://raw.githubusercontent.com/rafachurre/IoTChallenge_RaspPiGateway/master/Arduino_Keypad4x4_Servo_Ultrasounds_schematics.jpg)
