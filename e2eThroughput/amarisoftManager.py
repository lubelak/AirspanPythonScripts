# -*- coding: utf-8 -*-

from ping import pingHost
from readINI import readOption, readSection
from ssh import ssh
import logging
import logger
import time



class AmarisoftManager:
    def __init__(self, amarisoft_ip, username, password):
        self.amarisoft_ip = amarisoft_ip
        self.username = username
        self.password = password
        # self.amarisoft_connection
        # self.stop_event = threading.Event()

    def connect(self):
        # połączenie do amarisoft
        self.amarisoft_connection = ssh(self.amarisoft_ip, self.username, self.password)  # utworzenie obiektu ssh
        self.amarisoft_connection.openShell()  # odpalanie indywidualnej powloki aby byla mozliwosc wprowadzania kilku komend nastepujacych po sobie
        self.amarisoft_connection.readShell()  # wczytujemy pierwsze śmieci po podłączeniu się po ssh
        logging.info('Established connection to Amarisoft')
        time.sleep(0.5)
        self.amarisoft_connection.sendShell('sudo bash')
        time.sleep(0.5)
        self.amarisoft_connection.sendShell(self.password)
        time.sleep(0.5)
        output = self.amarisoft_connection.readShell()
        if 'root' in output:
            logging.info('Logged in as root')
        else:
            logging.error('Could not log in as root !!!')

    def disconnect(self):
        self.amarisoft_connection.closeConnection()

    def checkEnbStatus(self):
        # self.amarisoft_connection.readShell()  # wczytujemy pierwsze śmieci
        self.amarisoft_connection.sendShell('service lte status')
        time.sleep(0.5)
        self.amarisoft_connection.sendShell('\x03')
        time.sleep(0.1)
        output = self.amarisoft_connection.readShell()
        # print output
        if 'running' in output:
            logging.info('eNB is running')
            return True
        else:
            logging.info('eNB is not running')
            return False


    def stopEnb(self):
        self.amarisoft_connection.sendShell('service lte stop')

    def startEnb(self):
        self.amarisoft_connection.sendShell('service lte restart')

    def setProfile(self, profile_path):
        self.stopEnb()
        time.sleep(0.5)
        self.amarisoft_connection.sendShell('rm /root/enb/config/enb.cfg')
        time.sleep(0.1)
        self.amarisoft_connection.readShell()
        self.amarisoft_connection.sendShell('ln -s %s /root/enb/config/enb.cfg' % profile_path)
        time.sleep(0.2)
        self.amarisoft_connection.sendShell('ll /root/enb/config/enb.cfg')
        time.sleep(0.3)
        output = self.amarisoft_connection.readShell()
        if profile_path in output:
            logging.info('Profile set up properly')
        else:
            logging.error('Failed to set up new profile')
            exit(1)
        self.startEnb()
        time.sleep(0.5)
        if  self.checkEnbStatus():
            logging.info('eNB is runnig with profile %s' % profile_path)
        else:
            logging.error('eNB is not running with profile %s' % profile_path)

