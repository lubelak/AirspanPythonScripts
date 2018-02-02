# -*- coding: utf-8 -*-
import logging
import socket
import iperf3
import multiprocessing
import threading
import paramiko
import os
import errno
import platform
import time
from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.proto import rfc1902
import serial

#Dane snmp dla listwy zasilającej
SNMP_PUBLIC_COMMUNITY_POWER_SOCKET = 'public'               #dane do snmp
SNMP_PRIVATE_COMMUNITY_POWER_SOCKET = 'private'
SNMP_PORT_POWER_SOCKET = 161
SNMP_HOST_POWER_SOCKET = '10.11.4.72'             #adres IP Power Socket


#Dane snmp dla iB460 FT
SNMP_COMMUNITY_FT = 'public'               #dane do snmp
SNMP_PORT_FT = 161
SNMP_HOST_FT = '192.168.0.111'             #adres lokalny FT, po IPv6 nie mozna bylo pobrac informacji po snmp
SNMP_HOST6_FT = 'fe80::c6ed:baff:fea3:0482'

#dane do ssh iB460
LOCAL_USER = 'admin'
LOCAL_PASSWORD = 'HeWGEUx66m=_4!ND'

#sciezka gdzie zapisywane sa logi
MAIN_LOG_PATH = './MainLogIP.log'

#plik wynikowy
RESULTS_PATH = './WarmScanList_results.csv'
LOG_PATH = './Logs/LogReboot'                                  #log serialowy z FT


SERIAL_PORT = '/dev/ttyUSB0'
SERIAL_BAUDRATE = 115200



#TIMEOUT = 500000                      #czas testu w sekundach

#liczba rebootow, w tym przypadku cold reboot poprzez odlaczenie zasilania
MAX_REBOOT_COUNTER = 500

#ile minut ft ma na rejestracje
MAX_REG_TIMER = 20

#gniazdo które bierze udzial w tescie
out_inv = 'out1'

# #Gniazda ktore beda braly udzial w tescie
# out_inv = { 'out0': False,
#             'out1': True,
#             'out2': False,
#             'out3': False,
#             'out4': False
# }

# #Czas pracy poszczegolnego gniazda w sekundach
# out_up_time = { 'out0': 3000,
#                 'out1': 600,
#                 'out2': 180,
#                 'out3': 240,
#                 'out4': 20
# }
#
# #Czas uspienia/wylaczenia
# out_sleep_time = {'out0': 3000,
#                   'out1': 30,
#                   'out2': 180,
#                   'out3': 240,
#                   'out4': 200
# }

oid_table = {'out0': '.1.3.6.1.4.1.17095.3.1.0',
             'out1': '.1.3.6.1.4.1.17095.3.2.0',
             'out2': '.1.3.6.1.4.1.17095.3.3.0',
             'out3': '.1.3.6.1.4.1.17095.3.4.0',
             'out4': '.1.3.6.1.4.1.17095.3.5.0'
             }



def setRootLogger ():
    # set up logging to file - see previous section for more details
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(name)-20s %(levelname)-10s %(message)s',
                        datefmt='%d-%m-%y %H:%M:%S',
                        filename= MAIN_LOG_PATH,
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
        logging.info("Unknown operating system")
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

#funkcja wlaczajaca gniazdo
def snmpTurnOnOut(out):
    errorIndication, errorStatus, errorIndex, \
    varBinds = cmdgen.CommandGenerator().setCmd(
        cmdgen.CommunityData(SNMP_PRIVATE_COMMUNITY_POWER_SOCKET),
        cmdgen.UdpTransportTarget((SNMP_HOST_POWER_SOCKET, SNMP_PORT_POWER_SOCKET)),
        (oid_table[out], rfc1902.Integer(0))
    )
    logging.info('Turn on: %s'%out)

#funkcja wylaczajaca gniazdo
def snmpTurnOffOut(out):
    errorIndication, errorStatus, errorIndex, \
    varBinds = cmdgen.CommandGenerator().setCmd(
        cmdgen.CommunityData(SNMP_PRIVATE_COMMUNITY_POWER_SOCKET),
        cmdgen.UdpTransportTarget((SNMP_HOST_POWER_SOCKET, SNMP_PORT_POWER_SOCKET)),
        (oid_table[out], rfc1902.Integer(1))
    )
    logging.info('Turn off: %s'%out)


# #funkcja sprawdzajaca status gniazda, True znaczy włączone, False wyłączone
# def snmpCheckOut(out):
#     errorIndication, errorStatus, errorIndex, \
#     varBinds = cmdgen.CommandGenerator().getCmd(
#         cmdgen.CommunityData(SNMP_PUBLIC_COMMUNITY_POWER_SOCKET),
#         cmdgen.UdpTransportTarget((SNMP_HOST_POWER_SOCKET, SNMP_PORT_POWER_SOCKET)),
#         oid_table[out]
#     )
#     for name, val in varBinds:
#         if val==0:
#             logging.info('%s status: ON'%out)
#             return True
#         else:
#             logging.info('%s status: OFF'%out)
#             return False

# #funkcja wlaczajaca wszystkie gniazda- stan poczatkowy
# def snmpTurnOnAllOuts():
#     for oid_key in oid_table:
#         errorIndication, errorStatus, errorIndex, \
#         varBinds = cmdgen.CommandGenerator().setCmd(
#             cmdgen.CommunityData(SNMP_PRIVATE_COMMUNITY),
#             cmdgen.UdpTransportTarget((SNMP_HOST, SNMP_PORT)),
#             (oid_table[oid_key], rfc1902.Integer(0))
#         )
#         logging.info('Turn on: %s'%oid_key)
#         # time.sleep(1)

# #funkcja wlaczajaca i wylaczajaca gniazdo po odpowiedniej liczbie sekund zdefiniowanej w slownikach na poczatku skryptu
# def snmpScheduler(out):
#     while True:
#         time.sleep(out_up_time[out])    #odczekanie odpowiedniej liczby sekund jaka ma byc wlaczone gniazdo
#         snmpTurnOffOut(out)             #wylaczenie gniazda
#         time.sleep(out_sleep_time[out]) #liczba sekund przez jaka ma byc wylaczone gniazdo
#         snmpTurnOnOut(out)              #uruchomienie gniazda

#klasa do obslugi ssh
class ssh:
    client = None
    shell = None

    def __init__(self, address, username, password):
        logging.info("Connecting to server")
        self.client = paramiko.client.SSHClient()  # Utworzenie notwego klienta SSH
        self.client.set_missing_host_key_policy(
            paramiko.client.AutoAddPolicy())  # sprawia że paramiko podczas  łączenia ignoruje komunikat o nieznanym kluczu hosta i automatycznie go zatwierdza (przeważnie wymagane podczas pierwszego połączenia
        try:
            self.client.connect(address, username=username, password=password, look_for_keys=False,
                                allow_agent=False)
        except (socket.error, paramiko.AuthenticationException, paramiko.SSHException) as message:
            logging.info("Error: SSH connection to %s failed %s " % (address, str(message)))
            exit(1)

    def closeConnection(self):
        if (self.client != None):
            self.client.close()
            logging.info("SSH connection has been terminated")

    def openShell(self):
        self.shell = self.client.invoke_shell()

    def sendCommand(self, command):
        if (self.client):
            stdin, stdout, stderr = self.client.exec_command(
                command)  # wykorzystujac exec_command jest otwierana nowa powloka (shell) wiec nie da rady zmienic uzytkownika z admin na root, potrzeba utworzyc osobna powloke
            out = stdout.read()
            logging.info(out)
        else:
            logging.info("Connection not opened.")

    def sendShell(self, command):
        if (self.shell):
            self.shell.send(command + "\n")
        else:
            logging.info("Shell not opened.")

    def readShell(self):
        i = 0
        while not self.shell.recv_ready():  # Wait for the server to read and respond
            time.sleep(0.1)
            if i < 20:
                pass
            else:
                logging.info("Empty buffer")
                break
            i = i + 1

        time.sleep(1)  # wait enaough for writing to (hopefully) be finishe
        if self.shell.recv_ready():
            result = self.shell.recv(9999)  # read in
        else:
            logging.info("Still buffer is empty")
            result = "empty string"
        # print result
        return result

#funkcja usuwająca plik WarmScanList z FT
def deleteWarmScanListFile():
    connection = ssh(SNMP_HOST_FT, LOCAL_USER, LOCAL_PASSWORD)  # utworzenie obiektu ssh
    connection.openShell()  # odpalanie indywidualnej powloki aby byla mozliwosc wprowadzania kilku komend nastepujacych po sobie
    connection.sendShell("sudo rm /config/ft/sysdata.pdb")
    time.sleep(1)
    connection.sendShell("%s" % LOCAL_PASSWORD)
    time.sleep(1)
    logging.info("WarmScanList file has been deleted")
    connection.closeConnection()

#funkcja sprawdzajaca w jakim stanie aktualnie znajduje sie ft
def checkNetEntryState(ip, community, port, ipv6 = False):
    if pingHost(ip):
        if ipv6 :
            errorIndication, errorStatus, errorIndex, \
            varBinds = cmdgen.CommandGenerator().getCmd(
                cmdgen.CommunityData(SNMP_COMMUNITY_FT),
                cmdgen.Udp6TransportTarget((SNMP_HOST6_FT, SNMP_PORT_FT)),
                '1.3.6.1.4.1.989.1.21.1.3.6.1.15.1'
            )
            for name, val in varBinds:
                logging.info(val.prettyPrint())
                return str(val.prettyPrint())
        else:
            errorIndication, errorStatus, errorIndex, \
            varBinds = cmdgen.CommandGenerator().getCmd(
                cmdgen.CommunityData(SNMP_COMMUNITY_FT),
                cmdgen.UdpTransportTarget((SNMP_HOST_FT, SNMP_PORT_FT)),
                '1.3.6.1.4.1.989.1.21.1.3.6.1.15.1'
            )
            for name, val in varBinds:
                logging.info(val.prettyPrint())
                return str(val.prettyPrint())

def constReadSerialToFile( stop_event, reboot_nr):
    if not os.path.exists(os.path.dirname(LOG_PATH)):
        try:
            os.makedirs(os.path.dirname(LOG_PATH))
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise

    file_log_name = '%s_%i.log' % (LOG_PATH, reboot_nr + 1)
    logging.info('Path to serial log: %s' % file_log_name)
    file_l = open(file_log_name, "w")  # tworzenie pliku wynikowego
    ser = serial.Serial(SERIAL_PORT, SERIAL_BAUDRATE, timeout=0.050)        #obiekt serial

    ser.flushInput()
    ser.flushOutput()       #czyszczenie buforow
    while (not stop_event.is_set()):
        if ser.in_waiting:          #sprawdzenie czy cos jest do odebrania
            serial_output = ser.readline()
            file_l.write(serial_output)
    file_l.close()
    logging.info("Log file closed")
    ser.close()             #zamkniecie polaczenia serialowego



####  OD TEGO MIEJSCA STARTUJE SKRYPT  ####

setRootLogger()  # utoworzenie root Loggera, teraz zamiast print należy pisać logging.info('


#tworzenie pliku wynikowego
file_r = open(RESULTS_PATH,"w")
file_r.write("Reboot Number;Registration Time")
file_r.close()

#sprawdzenie czy listwa jest pingowalna, nawet jesli nie jest to test leci dalej- brak czasu na obsluge bledow
if pingHost(SNMP_HOST_POWER_SOCKET):
    logging.info("IP Power Socket is reachable")
else:
    logging.info("No response from IP Power Socket")

#sprawdzenie czy FT jest pingowalne po interfejsie eth (internal) nie po radiowym (tap0)
if pingHost(SNMP_HOST_FT):
    logging.info("FT is reachable")
else:
    logging.info("No response from FT")

#usunięcie pliku WarmScanList z FT
deleteWarmScanListFile()

#czas dla mnie na weryfikacje czy faktycznie plik zostal usuniety
time.sleep(120)


power_on_time = 0       #czas wlaczenia zasilania
reg_compl_time = 0      #czas po ktorym zarejestrowalo sie urzadzenie
elapsed_time = 0        #czas jaki uplynal

#glowna petla
for i in range(MAX_REBOOT_COUNTER):

    snmpTurnOffOut(out_inv)        #wylaczenie gniazda
    time.sleep(5)

    #uruchominie watku logowania serialowego
    stop_thread = threading.Event()
    thread = threading.Thread(target=constReadSerialToFile, args=(stop_thread, i)).start()

    snmpTurnOnOut(out_inv)         #wlaczenie gniazda
    power_on_time = time.time()     #zapis czasu

    logging.info("waiting 60s ")    #odczekanie az urzadzenie sie uruchomi
    time.sleep(60)

    while (time.time() - power_on_time) <= (MAX_REG_TIMER * 60):
        currentNetState = checkNetEntryState((SNMP_HOST_FT), SNMP_COMMUNITY_FT, SNMP_PORT_FT, False)
        if(currentNetState == 'RegistrationComplete'):  # sprawdzenie statusu rf
            logging.info("Net status: RegistrationComplete")
            reg_compl_time = time.time()
            elapsed_time = reg_compl_time - power_on_time
            logging.info("FT established radio connection to FB within : ")
            logging.info(time.strftime("%H:%M:%S", time.gmtime(elapsed_time)))
            logging.info('120s: time to establish connection and save warmScanList ')
            time.sleep(120)         #time to establish connection and save warmScanList
            break
        else:
            time.sleep(2)
            logging.info("Net status other than RegistrationComplete: %s"%currentNetState)
    else:
        elapsed_time = 0
        logging.info("Registration process took more time than %i mins. Rebooting..." % MAX_REG_TIMER)

    file_r = open(RESULTS_PATH, "a")  # dodanie liczby porzadkowej kazdego rebootu i czasu rejestracji
    file_r.write("\n%i;" % (i + 1))
    file_r.write(time.strftime("%H:%M:%S", time.gmtime(elapsed_time)))
    file_r.close()

    #wylaczenie watku logowania serialowego
    stop_thread.set()
    time.sleep(1)

logging.info("END OF SCRIPT")