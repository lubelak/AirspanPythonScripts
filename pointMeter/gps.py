# -*- coding: utf-8 -*-

import logging
import time
import pynmea2
try:
    import serial
except:
    logging.error('PySerial library is required to run this script, please install')
    exit(1)


class GpsManager():
    def __init__(self):
        self.gps_gga_dict = {}
        self.ser = None

    def connect(self, port, baud=9600):
        try:
            self.ser = serial.Serial(port, baud)
            logging.info('Properly connect to port: %s' % port)
        except serial.SerialException as s:
            logging.error(s)
            logging.error('Please disconnect other divece from this COM port')
            exit(1)

    def refresh(self):
            self.ser.reset_input_buffer()
            while True:
                line = self.ser.readline()
                line = line.strip()
                if '$GPGGA' in line:
                    logging.info(line)
                    msg = pynmea2.parse(line)
                    try:
                        self.gps_gga_dict['timestamp'] = msg.timestamp
                        self.gps_gga_dict['lat'] = msg.lat
                        self.gps_gga_dict['lat_dir'] = msg.lat_dir
                        self.gps_gga_dict['lon'] = msg.lon
                        self.gps_gga_dict['lon_dir'] = msg.lon_dir
                        self.gps_gga_dict['gps_qual'] = msg.gps_qual
                        self.gps_gga_dict['num_sats'] = msg.num_sats
                        self.gps_gga_dict['horizontal_dil'] = msg.horizontal_dil
                        self.gps_gga_dict['altitude'] = msg.altitude
                        self.gps_gga_dict['altitude_units'] = msg.altitude_units
                        self.gps_gga_dict['geo_sep'] = msg.geo_sep
                        self.gps_gga_dict['geo_sep_units'] = msg.geo_sep_units
                        self.gps_gga_dict['age_gps_data'] = msg.age_gps_data
                        self.gps_gga_dict['ref_station_id'] = msg.ref_station_id
                        self.gps_gga_dict['latitude'] = msg.latitude
                        self.gps_gga_dict['longitude'] = msg.longitude
                        logging.info('Properly GGA message was parsed:')
                        logging.info(self.gps_gga_dict)
                        break
                    except AttributeError:
                        logging.warning('Waiting for proper data')

    def getCoordinates(self):
        self.refresh()
        return self.gps_gga_dict

    def disconnect(self):
        self.ser.close()

# gps = GpsManager()
# gps.connect('COM12')
# print gps.getCoordinates()
# gps.disconnect()

