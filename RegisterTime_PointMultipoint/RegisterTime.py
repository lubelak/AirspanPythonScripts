# -*- coding: utf-8 -*-
from pysnmp.hlapi import *
import os
import platform
import time
import logging
import paramiko
import socket
import iperf3
import multiprocessing

from pysnmp.entity.rfc3413.oneliner import cmdgen

IP_FT1 = '10.18.0.31'
# IP_FT2 = '10.18.0.32'

MAX_REBOOT_COUNTER = 50

MAIN_LOG_PATH = '/home/airspan/Desktop/PythonResults/RegisterTime/MainLog.log'
RESULTS_PATH = '/home/airspan/Desktop/PythonResults/RegisterTime/Results.csv'

USERNAME = 'admin'
PASSWORD = 'HeWGEUx66m=_4!ND'

def pingHost(ip):
    oper = platform.system()  # Sprawdzenie z jakim systemem operacyjnym mamy do czynienie
    if (oper == "Windows"):  # Jest to ważne w stosunku jakiej komendy ping mamy użyć
        # print "This is Windows system"
        ping1 = "ping -n 1 "
    elif (oper == "Linux" and ip[0] != "f"):
        # print "This is Linux system"
        ping1 = "ping -c 1 "
    elif (oper == "Linux" and ip[0] == "f"):
        ping1 = "ping6 -c 1  "
    else:
        print "Unknown operating system"
        # ping1 = "ping -c 1 "

    comm = ping1 + ip  # utworzenie komendy jaka ma być wykonana w systemie
    logging.info("Ping command: %s"%comm)
    response = os.popen(comm)  # otwarcie pipe z komendą do pingowania wybranego adresu
    for line in response.readlines():  # wczytanie całej odpowiedzi (do EOF) jako listy poszczególnych linii
        if (line.count("Reply") or line.count(
                "ttl")):  # sprawdzenie czy poszczególne linie zawierają słówko TTL (dla Windowsa) i ttl (dla Linuxa), jeśli tak oznacz to że jest odpowiedź od hosta.
            logging.info(line.strip())  # Metoda Count() zwraca ile razy słowo występuje w liście
            # print ip, "--> Live"
            response.close()
            return True
            break
    logging.info("No response from host: %s"%ip)
    return False

def setRootLogger():
    # set up logging to file - see previous section for more details
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(name)-20s %(levelname)-10s %(message)s',
                        datefmt='%d-%m-%y %H:%M:%S',
                        filename=MAIN_LOG_PATH,
                        filemode='w')

    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(asctime)s %(name)-20s: %(levelname)-10s %(message)s', '%d-%m-%y %H:%M:%S')
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger('').addHandler(console)



class ssh:
    client = None
    shell = None

    def __init__(self, address, username, password):
        logging.info("Connecting to server")
        self.password = password
        self.client = paramiko.client.SSHClient()  # Utworzenie notwego klienta SSH
        self.client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())  # sprawia że paramiko podczas  łączenia ignoruje komunikat o nieznanym kluczu hosta i automatycznie go zatwierdza (przeważnie wymagane podczas pierwszego połączenia
        try:
            self.client.connect(address, username=username, password=password, look_for_keys=False, allow_agent=False)
        except (socket.error, paramiko.AuthenticationException, paramiko.SSHException) as message:
            logging.info("Error: SSH connection to %s failed %s "%(address, str(message)))
            exit(1)

    def closeConnection(self):
        if (self.client != None):
            self.client.close()
            logging.info("SSH connection has been terminated")

    def openShell(self):
        self.shell = self.client.invoke_shell()

    def sendCommand(self, command):
        if (self.client):
            stdin, stdout, stderr = self.client.exec_command(command)                   #wykorzystujac exec_command jest otwierana nowa powloka (shell) wiec nie da rady zmienic uzytkownika z admin na root, potrzeba utworzyc osobna powloke
            out = stdout.read()
            logging.info(out)
        else:
            logging.info("Connection not opened.")

    def sendShell(self, command):
        if (self.shell):
            self.shell.send(command + "\n")
        else:           logging.info("Shell not opened.")

    def readShell(self):
        i = 0
        while not self.shell.recv_ready():                                              #Wait for the server to read and respond
            time.sleep(0.1)
            if i < 20:
                pass
            else:
                logging.info("Empty buffer")
                break
            i = i + 1

        time.sleep(1)                                                                 #wait enaough for writing to (hopefully) be finishe
        if self.shell.recv_ready():
            result = self.shell.recv(9999)                                                     #read in
        else:
            logging.info("Still buffer is empty")
            result = "empty string"
        #print result
        return result
    def setRootAccount(self):
        self.sendShell("sudo su")
        time.sleep(1)
        self.sendShell(self.password)
        logging.info('Switch to root account')

def rebootFunction(ip):
    connection = ssh(ip, USERNAME, PASSWORD)  # utworzenie obiektu ssh
    connection.openShell()  # odpalanie indywidualnej powloki aby byla mozliwosc wprowadzania kilku komend nastepujacych po sobie
    connection.sendShell("sudo reboot")
    time.sleep(1)
    connection.sendShell(PASSWORD)
    logging.info("reboot command to host: %s"%ip)
    time.sleep(1)
    connection.closeConnection()

file_r = open(RESULTS_PATH, "w")  # tworzenie pliku wynikowego
file_r.write("Reboot nr; Registration Time FT1")
file_r.close()

setRootLogger()
logging.info("Pierwszy wpis")

while not(pingHost(IP_FT1)):# and pingHost(IP_FT2)):
    logging.info("FTs unreachable")
logging.info("FTs avaible")

for i in range(MAX_REBOOT_COUNTER):
    rebootFunction(IP_FT1)
    reboot_time_ft1 = time.time()
    logging.info("Waiting 45s...")
    time.sleep(45)

    # rebootFunction(IP_FT2)
    # reboot_time_ft2 = time.time()
    while not (pingHost(IP_FT1)):# and pingHost(IP_FT2)):
        logging.info("FTs unreachable")
        time.sleep(1)

    register_time = time.time()
    elapsed_time = register_time - reboot_time_ft1
    logging.info(time.strftime("%H:%M:%S", time.gmtime(elapsed_time)))
    file_r = open(RESULTS_PATH, "a")  # tworzenie pliku wynikowego
    file_r.write("\n%i;"%i)
    file_r.write(time.strftime("%H:%M:%S", time.gmtime(elapsed_time)))
    file_r.close()

    j=0
    while j<5:
        if(pingHost(IP_FT1)):# and pingHost(IP_FT2)):
            j+=1
            logging.info("Register confirmation nr: %i"%j)
        else:
            logging.info("One of FTs lose connection")
