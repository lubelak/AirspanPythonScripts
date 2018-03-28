# -*- coding: utf-8 -*-

import logging
import os, errno
from ssh import ssh
import time
import ping
import threading

PATH = r'C:\Users\klubelski\Desktop\LOGS\PythonLogs'
NAME = 'log1'
IP = '169.254.1.1'
USERNAME = 'admin'
PASS = 'HeWGEUx66m=_4!ND'

class NodeLogger:
    def __init__(self, node_ip='169.254.1.1', username='admin', password='HeWGEUx66m=_4!ND', log_path=None , log_name=None):
        self.log_path = log_path
        self.log_name = log_name
        self.node_ip = node_ip
        self.username = username
        self.password = password
        self.stop_event = threading.Event()

    def createPath(self):
        ### LINUX ####
        # if not os.path.exists(os.path.dirname(self.log_path)):
        #     try:
        #         os.makedirs(os.path.dirname(self.log_path))
        #     except OSError as exc:  # Guard against race condition
        #         if exc.errno != errno.EEXIST:
        #             print exc
        #             logging.error('Directory could not be created')
        #             raise
        ### WINDOWS ####
        if not os.path.exists(self.log_path):
            try:
                os.makedirs(self.log_path)
            except OSError as exc:  # Guard against race condition
                if exc.errno != errno.EEXIST:
                    print exc
                    logging.error('Directory could not be created')
                    raise

    def startLogging(self):
        thread = threading.Thread(target=self.runLogging).start()

    def stopLogging(self):
        self.stop_event.set()

class RelayLogger(NodeLogger):
    def __init__(self, log_path, log_name, node_ip, username, password):
        NodeLogger.__init__(self, log_path, log_name, node_ip, username, password)
        self.relay_connection = None

    def runLogging(self):
        self.relay_connection = ssh(self.node_ip, self.username, self.password)  # utworzenie obiektu ssh
        self.createPath()
        file_log_name = '%s\%s.log' % (self.log_path, self.log_name)
        logging.info('Path to serial log: %s' % file_log_name)
        file_l = open(file_log_name, "w")  # tworzenie pliku wynikowego

        self.relay_connection.openShell()  # odpalanie indywidualnej powloki aby byla mozliwosc wprowadzania kilku komend nastepujacych po sobie
        output = self.relay_connection.readShell()  # wczytujemy pierwsze śmieci po podłączeniu się po ssh
        print output
        self.relay_connection.sendShell('/bs/tnet')
        logging.info('./tnet command')
        time.sleep(1)
        output = self.relay_connection.readShell()
        while output.find("Connected to DGS server") == -1:
            logging.warning('Waiting for tnet')
            time.sleep(1)
            output = self.relay_connection.readShell()
        logging.info('Connected to DGS server')
        time.sleep(0.5)

        self.relay_connection.sendShell('event -t board -uedebug')
        logging.info('UE debug command')
        time.sleep(0.5)

        while (not self.stop_event.is_set()):
            tnet_output = self.relay_connection.readShell()
            file_l.write(tnet_output)
            time.sleep(1)
        file_l.close()
        logging.info("Log file closed")
        self.relay_connection.closeConnection()  # zamkniecie polaczenia serialowego
        # while (not self.stop_event.is_set()):
        #     print 'dupa'
        #     time.sleep(2)

    def getIIB(self, table_nr):
        self.relay_connection = ssh(self.node_ip, self.username, self.password)  # utworzenie obiektu ssh
        self.relay_connection.openShell()  # odpalanie indywidualnej powloki aby byla mozliwosc wprowadzania kilku komend nastepujacych po sobie
        output = self.relay_connection.readShell()  # wczytujemy pierwsze śmieci po podłączeniu się po ssh
        self.relay_connection.sendShell('/bs/tnet')
        logging.info('./tnet command')
        time.sleep(1)
        output = self.relay_connection.readShell()
        while output.find("Connected to DGS server") == -1:
            logging.warning('Waiting for tnet')
            time.sleep(1)
            output = self.relay_connection.readShell()
        logging.info('Connected to DGS server')
        time.sleep(0.5)
        self.relay_connection.readShell()
        self.relay_connection.sendShell('get -vv %i' % table_nr)
        logging.info('get -vv %i command' % table_nr)
        time.sleep(0.2)
        output = self.relay_connection.readShell()
        print output
        self.relay_connection.closeConnection()
# output2 = ping.pingHost(IP)
# print output2
# time.sleep(3)
# relay = RelayLogger(PATH, NAME, IP, USERNAME, PASS)
# relay.startLogging()
# print 'poczatek'
# time.sleep(15)
# relay.stopLogging()
# print 'koniec'




