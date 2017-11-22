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


REMOTE_IP = '10.18.0.203'               #dane do logowania po ssh do serwera
USERNAME = 'administrator'
PASSWORD = 'localadmin'

SNMP_COMMUNITY = 'public'               #dane do snmp
SNMP_PORT = 161
SNMP_HOST = '192.168.0.111'             #adres lokalny FT, po IPv6 nie mozna bylo pobrac informacji po snmp
SNMP_HOST6 = 'fe80::c6ed:baff:fea3:0482'

LOCAL_USER = 'admin'                    #dane do ssh do iB460
LOCAL_PASSWORD = 'HeWGEUx66m=_4!ND'

REMOTE_SERVER_IP = '192.168.0.203'      #dane do iperfa
REMOTE_PORT_1 = 5211
REMOTE_PORT_2 = 5222
DURATION = 60
RESULTS_PATH = "/home/airspan/Desktop/PythonResults/ThroughputAfterReboot_results.csv"          #wyniki
MAIN_LOG_PATH = '/home/airspan/Desktop/PythonResults/MainLog.log'                               #log z wykonywania sie programu
LOG_PATH = '/home/airspan/Desktop/PythonResults/Log/LogReboot'                                  #log serialowy z FT
MAX_REBOOT_COUNTER = 100

SERIAL_PORT = '/dev/ttyUSB0'
SERIAL_BOUDRATE = 115200

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

class ssh:
    client = None
    shell = None

    def __init__(self, address, username, password):
        logging.info("Connecting to server")
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

    # def sendCommand(self, command):
    #     if (self.client):
    #         stdin, stdout, stderr = self.client.exec_command(command)
    #         while not stdout.channel.exit_status_ready():
    #             # Print data when available
    #             if stdout.channel.recv_ready():
    #                 alldata = stdout.channel.recv(1024)
    #                 prevdata = b"1"
    #                 while prevdata:
    #                     prevdata = stdout.channel.recv(1024)
    #                     alldata += prevdata
    #
    #                 print(str(alldata))
    #     else:
    #         print("Connection not opened.")


def createClient(q, server_ip, port,duration, reverse = False):
    result_d = {}
    client = iperf3.Client()
    client.duration = duration
    client.server_hostname = server_ip
    client.port = port
    client.reverse = reverse
    # client.json_output = False
    result = client.run()
    # print result.sent_Mbps
    if reverse == False :
        # print "reverse == False"
        q.put({'UL':result.sent_Mbps})
    else:
        q.put({'DL': result.sent_Mbps})
        # print "reverse == True"

def checkNetEntryState(ip, community, port, ipv6 = False):
    if pingHost(ip):
        if ipv6 :
            errorIndication, errorStatus, errorIndex, \
            varBinds = cmdgen.CommandGenerator().getCmd(
                cmdgen.CommunityData(SNMP_COMMUNITY),
                cmdgen.Udp6TransportTarget((SNMP_HOST6, SNMP_PORT)),
                '1.3.6.1.4.1.989.1.21.1.3.6.1.15.1'
            )
            for name, val in varBinds:
                logging.info(val.prettyPrint())
                return str(val.prettyPrint())
        else:
            errorIndication, errorStatus, errorIndex, \
            varBinds = cmdgen.CommandGenerator().getCmd(
                cmdgen.CommunityData(SNMP_COMMUNITY),
                cmdgen.UdpTransportTarget((SNMP_HOST, SNMP_PORT)),
                '1.3.6.1.4.1.989.1.21.1.3.6.1.15.1'
            )
            for name, val in varBinds:
                logging.info(val.prettyPrint())
                return str(val.prettyPrint())

def logSerialViaSsh(stop_event, reboot_nr):
    if pingHost(REMOTE_IP):                                     #połączenie sie do serwera zdalnego, odpalenie screena i logowanie do pliku
        logging.info("Remote ssh server available on ip: %s"%REMOTE_IP)
        connection = ssh(REMOTE_IP, USERNAME, PASSWORD)         # utworzenie obiektu ssh
        connection.openShell()                                  # odpalanie indywidualnej powloki aby byla mozliwosc wprowadzania kilku komend nastepujacych po sobie
        connection.sendShell('sudo su')
        time.sleep(1)
        connection.sendShell('localadmin')
        time.sleep(1)
        output = connection.readShell()
        # print output
        logging.info("Logging to server as root")
        connection.sendShell('pkill screen')
        logging.info("Killing all screen processes")
        thread = threading.Thread(target=constReadShellToFile, args=(connection, stop_event, reboot_nr)).start()



def constReadShellToFile(connect_obj,stop_event, reboot_nr):
    if not os.path.exists(os.path.dirname(LOG_PATH)):
        try:
            os.makedirs(os.path.dirname(LOG_PATH))
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise

    file_log_name = '%s%i.log' % (LOG_PATH, reboot_nr + 1)
    logging.info('Path to serial log: %s'%file_log_name)
    file_l = open(file_log_name, "w")  # tworzenie pliku wynikowego
    connect_obj.sendShell('screen %s %i' % (SERIAL_PORT, SERIAL_BOUDRATE))
    logging.info("screen command")
    time.sleep(1)
    useless_output = connect_obj.shell.recv(9999)
    # print useless_output
    while (not stop_event.is_set()):
        # connect_obj.sendShell('\n')
        if connect_obj.shell.recv_ready():
            serial_output = connect_obj.shell.recv(9999)
            file_l.write(serial_output)
            # print serial_output
            time.sleep(1)
    file_l.close()
    logging.info("Log file closed")
    connect_obj.closeConnection()
    # with open(file_log_name, 'w') as file_r:
    #     file_r.write("Reboot Number: %i" % (i + 1))




file_r = open(RESULTS_PATH,"w")                            #tworzenie pliku wynikowego
file_r.write("RebootNumber;DL;UL;Registration Time")
file_r.close()

setRootLogger()                                             #utoworzenie root Loggera, teraz zamiast print należy pisać logging.debug('

x= {}                                                       #nowy slownik dla wynikow
reboot_time = 0
reg_compl_time = 0
elapsed_time = 0

while True:
    if pingHost(REMOTE_IP):                                     #połączenie sie do serwera zdalnego i utworzenie demonow iperf3 -s
        logging.info("Remote server available")
        connection = ssh(REMOTE_IP, USERNAME, PASSWORD)         # utworzenie obiektu ssh
        connection.openShell()                                  # odpalanie indywidualnej powloki aby byla mozliwosc wprowadzania kilku komend nastepujacych po sobie
        connection.sendShell("iperf3 -s -D -p %i"%REMOTE_PORT_1)
        logging.info("Iperf3 daemon sever 1 initialized on port: %i"%REMOTE_PORT_1)
        time.sleep(1)
        connection.sendShell("iperf3 -s -D -p %i" % REMOTE_PORT_2)
        logging.info("Iperf3 daemon sever 2 initialized on port: %i" % REMOTE_PORT_2)
        connection.closeConnection()
        break
    else:
        logging.info("Remote server unavailable")
        time.sleep(1)



for i in range(MAX_REBOOT_COUNTER):
    stop_thread = threading.Event()
    logSerialViaSsh(stop_thread, i)



    connection = ssh((SNMP_HOST6+'%eno1'), LOCAL_USER, LOCAL_PASSWORD)  # utworzenie obiektu ssh
    connection.openShell()  # odpalanie indywidualnej powloki aby byla mozliwosc wprowadzania kilku komend nastepujacych po sobie
    connection.sendShell("reboot")
    reboot_time = time.time()
    logging.info("reboot command")
    time.sleep(2)
    connection.closeConnection()

    file_r = open(RESULTS_PATH, "a")  # dodanie liczby porzadkowej kazdego rebootu
    file_r.write("\n%i;" % (i + 1))
    file_r.close()

    logging.info("waiting 90s ")
    time.sleep(90)

    while ((checkNetEntryState((SNMP_HOST), SNMP_COMMUNITY, SNMP_PORT, False) != 'RegistrationComplete' ) or pingHost(REMOTE_SERVER_IP)!=True):         #sprawdzenie statusu rf i pinga do serwera zdalnego
        time.sleep(2)
        logging.info("Net status other than RegistrationComplete")

    reg_compl_time = time.time()
    elapsed_time = reg_compl_time - reboot_time
    logging.info("FT established radio connection to FB within : ")
    logging.info(time.strftime("%H:%M:%S", time.gmtime(elapsed_time)))

    logging.info("Device operational after reboot")
    logging.info(checkNetEntryState((SNMP_HOST), SNMP_COMMUNITY, SNMP_PORT, False))
    logging.info('waiting 180s to establishing connection')
    time.sleep(180)                      #czas na ustabilizowanie połączenia
    while (checkNetEntryState((SNMP_HOST), SNMP_COMMUNITY, SNMP_PORT, False) != 'RegistrationComplete' or pingHost(REMOTE_SERVER_IP)!=True):         #sprawdzenie statusu rf i pinga do serwera zdalnego
        time.sleep(2)

    q = multiprocessing.Queue()
    p1= multiprocessing.Process(target=createClient, args=(q,REMOTE_SERVER_IP, REMOTE_PORT_1, DURATION, False,))
    p2= multiprocessing.Process(target=createClient, args=(q,REMOTE_SERVER_IP, REMOTE_PORT_2, DURATION, True,))
    p1.start()
    logging.info("Process 1 is running")
    p2.start()
    logging.info("Process 2 is running")
    p1.join()
    p2.join()

    x = q.get()
    x.update(q.get())
    logging.info("DL: %f \nUL: %f"%(x['DL'],x['UL']))

    if x['DL'] < 100:
        logging.info("DL is too low")
        logging.info("Throughput test must be repeated")
        time.sleep(60)
        p1 = multiprocessing.Process(target=createClient, args=(q, REMOTE_SERVER_IP, REMOTE_PORT_1, DURATION, False,))
        p2 = multiprocessing.Process(target=createClient, args=(q, REMOTE_SERVER_IP, REMOTE_PORT_2, DURATION, True,))
        p1.start()
        logging.info("Process 1 is running")
        p2.start()
        logging.info("Process 2 is running")
        p1.join()
        p2.join()

        x = q.get()
        x.update(q.get())
        logging.info("DL: %f UL: %f" % (x['DL'], x['UL']))
        if x['DL'] < 100:
            logging.info("DL second time is too low")
            logging.info("Date and time:")
            logging.info(time.strftime("%c"))
            exit(1)
    else:
        logging.info("DL is as expected!!!")

    file_r = open(RESULTS_PATH, "a")  # dodanie wynikow DL i UL
    file_r.write("%f;%f;" % (x['DL'], x['UL']))
    file_r.write(time.strftime("%H:%M:%S", time.gmtime(elapsed_time)))
    file_r.close()

    stop_thread.set()


