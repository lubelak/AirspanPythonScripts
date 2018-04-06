# -*- coding: utf-8 -*-

import logger
import logging

# configuration
port = "COM10"
baud = 9600

try:
    from serial import serial
except:
    print "PySerial library is required to run this script, please install"
    exit(1)

def run():
    ser = serial.Serial(port, baud)
    try:
        while True:
            line = ser.readline()
            line = line.strip()
            print("Received: " + line)

    finally:
        ser.close()




if __name__ == '__main__':
    run()