#!/usr/bin/python3
import os
import subprocess
import re

p = subprocess.Popen(['i2cdetect', '-y','1'],stdout=subprocess.PIPE,)
#cmdout = str(p.communicate())

devices[]

for i in range(0,9):
  line = str(p.stdout.readline())

  for match in re.finditer("[0-9][0-9]:.*[0-9][0-9]", line):
    print (match.group())
    word = line.split(":")[1].split()
    for device in word:
    	devices.append(device)

print devices