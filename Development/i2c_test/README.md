# IoTChallenge_RaspPiGateway
This repository saves the code for the Raspberry Pi Gateway in the "NoFrontiers" project for the 2017 IoT Challenge

## 1. i2c_test
Features:
1. i2c communication enabled. Preapred to send/read certain codes to perform some actions in the slave
2. Prints a menu in the console to simulate the messages received from the Cloud

**MESSAGES MAPPING**
> i2c can send numbers from 0 to 255 in its simplest implementation. 

> The constants below are a collection of messages for the communication between Master <-> Slave. 

> Slaves (Arduinos) are always pasive. They don't insert data into the BUS unless Master calls for it. 

> If Master sends an ACTION code, the Slave will execute certain action in the actuators. 

> If Master wants to read some data, it needs to send a DATA_REQUEST code first. This will prepare the data to be sent in the Slave. Then Master can read() the bus in the Slave's address to get the data. 

> The data send from the Slave will be one of the SLAVE_STATUS messages.

<br> *SLAVE_STATUS_BOX_OPEN =* **1** //The box is open
<br> *SLAVE_STATUS_BOX_CLOSED =* **2** //The box is closed
<br> *SLAVE_STATUS_BOX_OPENCLOSED_UNKNOWN =* **3** //It is not clear if the box is open or closed (error handling)
<br> *SLAVE_STATUS_BOX_EMPTY =* **4** //The box is empty
<br> *SLAVE_STATUS_BOX_FULL =* **5** //The box is full
<br> *SLAVE_STATUS_BOX_EMPTYFULL_UNKNOWN =* **6** //It is not clear if the box is empty or full (error handling)
<br> *SLAVE_STATUS_LED_BLINKING =* **7** //The LED is blinking
<br> *SLAVE_STATUS_LED_OFF =* **8** //The LED is off
<br> *SLAVE_STATUS_LED_BLINKINGOFF_UNKNOWN =* **9** //It is not clear if the LED is blinking or off (error handling)

<br> *SLAVE_STATUS_NO_DATA_REQUEST_RECEIVED_PREVIOUSLY =* **50** //Return message when Master reads without writing a DATA_REQUEST message before
<br> *DATA_REQUEST_LAST_CODE_RECEIVED =* **51** //Master wants to read() the previous code received. Prepare "to_send" variable for a read event
<br> *DATA_REQUEST_STATUS_OPENCLOSE =* **52** //Master wants to read() the open/close status. Prepare "to_send" variable for a read event
<br> *DATA_REQUEST_STATUS_EMPTYFULL =* **53** //Master wants to read() the empty/full status. Prepare "to_send" variable for a read event

<br> *ACTION_REQUEST_OPEN_BOX =* **100** //Master requests to open the box
<br> *ACTION_REQUEST_CLOSE_BOX =* **101** //Master requests to close the box
<br> *ACTION_REQUEST_BLINK_LED =* **102** //Master requests to blink the LED
<br> *ACTION_REQUEST_TURN_OFF_LED =* **103** //Master requests to turn off the LED
<br> *ACTION_REQUEST_SET_KEYPAD_PWD =* **104** //Master requests to set a new password. A [0-255] password will be sent in the next write() byte


**HOW TO USE**

1. Download the code and execute it
```
python main.py
```
2. Select one of the options showed in the console
3. If the code is in the collection of available codes, it is sent to the Slave via i2c
4. After writing, a read() request is done to get the response from the Slave. Then it is printed in the console
