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

SNMP_COMMUNITY = 'public'
SNMP_PORT = 161
SNMP_HOST_FB = '10.18.0.210'
# SNMP_HOST_FT = 'fe80::c6ed:baff:fea3:0482'
SNMP_HOST_FT = '192.168.0.111'

MAIN_LOG_PATH = '/home/airspan/Desktop/PythonResults/MCS_adaptation/MainLog.log'
RESULTS_PATH = '/home/airspan/Desktop/PythonResults/MCS_adaptation/Results.csv'

REMOTE_SERVER_IP = '192.168.0.203'      #dane do iperfa
REMOTE_PORT_1 = 5211
REMOTE_PORT_2 = 5222
DURATION = 60

REMOTE_IP = '10.18.0.203'               #dane do logowania po ssh do serwera
USERNAME = 'administrator'
PASSWORD = 'localadmin'

PATH_ATT_APP = '/home/administrator/Desktop/VAUNIX/Linux\ app\ Kenny/'


#klasa przechowujaca statystyki liczby slotow wykorzystywanych przez poszczegolne msc'y
class StatsSlots:
    def __init__(self):
        self.stats_dl_slots = {'256qam56': 0,
                            '256qam34': 0,
                            '64qam56': 0,
                            '64qam34': 0,
                            '64qam23': 0,
                            '64qam12': 0,
                            '16qam34': 0,
                            '16qam12': 0,
                            'qpsk34': 0,
                            'qpsk12': 0
                            # 'mimo_a': 0,
                            # 'mimo_b': 0
                            }

        self.stats_dl_mimo = {'mimo_a': 0,
                              'mimo_b':0
                              }

        self.stats_ul_slots = {'256qam56': 0,
                            '256qam34': 0,
                            '64qam56': 0,
                            '64qam34': 0,
                            '64qam23': 0,
                            '64qam12': 0,
                            '16qam34': 0,
                            '16qam12': 0,
                            'qpsk34': 0,
                            'qpsk12': 0
                            # 'mimo_a': 0,
                            # 'mimo_b': 0
                            }

        self.stats_ul_mimo = {'mimo_a': 0,
                              'mimo_b':0
                              }
#funkcja parsujaca tablice statystyk otrzymana z zapytania snmp do odpowiedniego slownika
    def updateStatistics(self, bindTable):
        for varBindTableRow in bindTable:
            for name, val in varBindTableRow:
                # print '%s = %s' % (name.prettyPrint(), val.prettyPrint())
                if str(name) == '1.3.6.1.4.1.989.1.16.2.9.8.1.30.1':
                    self.stats_dl_slots['256qam56'] = int(val)
                elif str(name) == '1.3.6.1.4.1.989.1.16.2.9.8.1.29.1':
                    self.stats_dl_slots['256qam34'] = int(val)
                elif str(name) == '1.3.6.1.4.1.989.1.16.2.9.8.1.14.1':
                    self.stats_dl_slots['64qam56'] = int(val)
                elif str(name) == '1.3.6.1.4.1.989.1.16.2.9.8.1.13.1':
                    self.stats_dl_slots['64qam34'] = int(val)
                elif str(name) == '1.3.6.1.4.1.989.1.16.2.9.8.1.12.1':
                    self.stats_dl_slots['64qam23'] = int(val)
                elif str(name) == '1.3.6.1.4.1.989.1.16.2.9.8.1.11.1':
                    self.stats_dl_slots['64qam12'] = int(val)
                elif str(name) == '1.3.6.1.4.1.989.1.16.2.9.8.1.10.1':
                    self.stats_dl_slots['16qam34'] = int(val)
                elif str(name) == '1.3.6.1.4.1.989.1.16.2.9.8.1.9.1':
                    self.stats_dl_slots['16qam12'] = int(val)
                elif str(name) == '1.3.6.1.4.1.989.1.16.2.9.8.1.8.1':
                    self.stats_dl_slots['qpsk34'] = int(val)
                elif str(name) == '1.3.6.1.4.1.989.1.16.2.9.8.1.7.1':
                    self.stats_dl_slots['qpsk12'] = int(val)
                elif str(name) == '1.3.6.1.4.1.989.1.16.2.9.8.1.35.1':
                    self.stats_dl_mimo['mimo_a'] = int(val)
                elif str(name) == '1.3.6.1.4.1.989.1.16.2.9.8.1.36.1':
                    self.stats_dl_mimo['mimo_b'] = int(val)
                elif str(name) == '1.3.6.1.4.1.989.1.16.2.9.8.1.34.1':
                    self.stats_ul_slots['256qam56'] = int(val)
                elif str(name) == '1.3.6.1.4.1.989.1.16.2.9.8.1.33.1':
                    self.stats_ul_slots['256qam34'] = int(val)
                elif str(name) == '1.3.6.1.4.1.989.1.16.2.9.8.1.25.1':
                    self.stats_ul_slots['64qam56'] = int(val)
                elif str(name) == '1.3.6.1.4.1.989.1.16.2.9.8.1.24.1':
                    self.stats_ul_slots['64qam34'] = int(val)
                elif str(name) == '1.3.6.1.4.1.989.1.16.2.9.8.1.23.1':
                    self.stats_ul_slots['64qam23'] = int(val)
                elif str(name) == '1.3.6.1.4.1.989.1.16.2.9.8.1.22.1':
                    self.stats_ul_slots['64qam12'] = int(val)
                elif str(name) == '1.3.6.1.4.1.989.1.16.2.9.8.1.21.1':
                    self.stats_ul_slots['16qam34'] = int(val)
                elif str(name) == '1.3.6.1.4.1.989.1.16.2.9.8.1.20.1':
                    self.stats_ul_slots['16qam12'] = int(val)
                elif str(name) == '1.3.6.1.4.1.989.1.16.2.9.8.1.19.1':
                    self.stats_ul_slots['qpsk34'] = int(val)
                elif str(name) == '1.3.6.1.4.1.989.1.16.2.9.8.1.18.1':
                    self.stats_ul_slots['qpsk12'] = int(val)
                elif str(name) == '1.3.6.1.4.1.989.1.16.2.9.8.1.37.1':
                    self.stats_ul_mimo['mimo_a'] = int(val)
                elif str(name) == '1.3.6.1.4.1.989.1.16.2.9.8.1.38.1':
                    self.stats_ul_mimo['mimo_b'] = int(val)

#klasa porownujaca statystyki zebrane z roznych chwil czasowych i przechowujaca procentowe wartosci wykorzystywanych mcs'ow
class ComparisonStats:
    def __init__(self, stats_before, stats_after):
        self.stats_before = stats_before
        self.stats_after = stats_after
        self.stats_dl_per = {}
        self.stats_ul_per = {}
    def compareDLstats(self):
        result = {}
        for key in self.stats_before.stats_dl_slots.keys():
            result[key] = self.stats_after.stats_dl_slots[key] - self.stats_before.stats_dl_slots[key]
        sum_slots = sum(result.values())
        logging.info("Sum of DL slots: %i"%sum_slots)
        for key in result.keys():
            self.stats_dl_per[key] = round(((1.0*result[key]/sum_slots)*100), 2)
        logging.info(self.stats_dl_per)
        # return result
    def compareULstats(self):
        result = {}
        for key in self.stats_before.stats_ul_slots.keys():
            result[key] = self.stats_after.stats_ul_slots[key] - self.stats_before.stats_ul_slots[key]
        sum_slots = sum(result.values())
        logging.info("Sum of UL slots: %i" % sum_slots)
        for key in result.keys():
            self.stats_ul_per[key] = round(((1.0 * result[key] / sum_slots) * 100), 2)
        logging.info(self.stats_ul_per)
        # return result

#klasa przechowujaca informacje o RSSI, trzeba podac tablice z zapytania snmpRssiQuery oraz stan rejestracji
class rssiStatus:
    def __init__(self, rssi_table):
        self.rssi_d = {'rssi_ant_0': 0,
                       'rssi_ant_1': 0,
                       'rssi_avg': 0
                       }

        self.rssi_table = rssi_table
        self.net_entry_state = ''

        for varBindTableRow in self.rssi_table:
            for name, val in varBindTableRow:
                # print '%s = %s' % (name.prettyPrint(), val.prettyPrint())
                if str(name) == '1.3.6.1.4.1.989.1.21.1.3.6.1.38.1':
                    self.rssi_d['rssi_avg'] = int(val)
                elif str(name) == '1.3.6.1.4.1.989.1.21.1.3.6.1.39.1':
                    self.rssi_d['rssi_ant_0'] = int(val)
                elif str(name) == '1.3.6.1.4.1.989.1.21.1.3.6.1.40.1':
                    self.rssi_d['rssi_ant_1'] = int(val)
                elif str(name) == '1.3.6.1.4.1.989.1.21.1.3.6.1.15.1':
                    self.net_entry_state = str(val)
        for x in self.rssi_d:
            logging.info('%s : %i'%(x,self.rssi_d[x]))
        logging.info("Network state: %s"%self.net_entry_state)

    def rssiStatusUpdate(self, rssi_table):
        for varBindTableRow in rssi_table:
            for name, val in varBindTableRow:
                # print '%s = %s' % (name.prettyPrint(), val.prettyPrint())
                if str(name) == '1.3.6.1.4.1.989.1.21.1.3.6.1.38.1':
                    self.rssi_d['rssi_avg'] = int(val)
                elif str(name) == '1.3.6.1.4.1.989.1.21.1.3.6.1.39.1':
                    self.rssi_d['rssi_ant_0'] = int(val)
                elif str(name) == '1.3.6.1.4.1.989.1.21.1.3.6.1.40.1':
                    self.rssi_d['rssi_ant_1'] = int(val)
                elif str(name) == '1.3.6.1.4.1.989.1.21.1.3.6.1.15.1':
                    self.net_entry_state = str(val)
        for x in self.rssi_d:
            logging.info('%s : %i'%(x,self.rssi_d[x]))
        logging.info("Network state: %s"%self.net_entry_state)

    def checkRegistrationState(self):
        if self.net_entry_state == 'RegistrationComplete':
            print "FT is connected"
            return True
        else:
            print "FT is not connected"
            return False

# Funkcja ktora wykonuje zapytanie snmp i zwraca rssi
def snmpRssiQuery():
    errorIndication, errorStatus, errorIndex, \
    varBindTable = cmdgen.CommandGenerator().bulkCmd(
                cmdgen.CommunityData(SNMP_COMMUNITY),
                cmdgen.UdpTransportTarget((SNMP_HOST_FT, SNMP_PORT)),
                # cmdgen.UdpTransportTarget((SNMP_HOST, SNMP_PORT)),
                0,
                25,
                (1,3,6,1,4,1,989,1,21,1,3,6)                              #MIB Table asIbFtDiagDiagTable
                # (1,3,6,1,4,1,989,1,16,2,9,8)

            )

    if errorIndication:
       print errorIndication
    else:
        if errorStatus:
            print '%s at %s\n' % (
                errorStatus.prettyPrint(),
                errorIndex and varBindTable[-1][int(errorIndex)-1] or '?'
                )
        # else:
        #     for varBindTableRow in varBindTable:
        #         for name, val in varBindTableRow:
        #             print '%s = %s' % (name.prettyPrint(), val.prettyPrint())
    return varBindTable


# Funkcja ktora wykonuje zapytanie snmp i zwraca tablice statystyk odnosnie mcs i liczbie slotow
def snmpStatsQuery():
    errorIndication, errorStatus, errorIndex, \
    varBindTable = cmdgen.CommandGenerator().bulkCmd(
                cmdgen.CommunityData(SNMP_COMMUNITY),
                cmdgen.UdpTransportTarget((SNMP_HOST_FB, SNMP_PORT)),
                # cmdgen.UdpTransportTarget((SNMP_HOST, SNMP_PORT)),
                0,
                25,
                # (1,3,6,1,4,1,989,1,21,1,3,6),                              #MIB Table asIbFtDiagDiagTable
                (1,3,6,1,4,1,989,1,16,2,9,8)
                # (1,3,6,1,2,1,4,20), # ipAddrTable OID . This works fine.
                # (1,3,6,1,2,1,4,21), # ipRouteTable
                # (1,3,6,1,2,1,4,22), # ipNetToMediaTable
            )

    if errorIndication:
       logging.error(errorIndication)
       logging.info('Waiting for snmp response')
       time.sleep(3)

       errorIndication, errorStatus, errorIndex, \
       varBindTable = cmdgen.CommandGenerator().bulkCmd(
           cmdgen.CommunityData(SNMP_COMMUNITY),
           cmdgen.UdpTransportTarget((SNMP_HOST_FB, SNMP_PORT)),
           # cmdgen.UdpTransportTarget((SNMP_HOST, SNMP_PORT)),
           0,
           25,
           # (1,3,6,1,4,1,989,1,21,1,3,6),                              #MIB Table asIbFtDiagDiagTable
           (1, 3, 6, 1, 4, 1, 989, 1, 16, 2, 9, 8)
           # (1,3,6,1,2,1,4,20), # ipAddrTable OID . This works fine.
           # (1,3,6,1,2,1,4,21), # ipRouteTable
           # (1,3,6,1,2,1,4,22), # ipNetToMediaTable
       )
    else:
        if errorStatus:
            print '%s at %s\n' % (
                errorStatus.prettyPrint(),
                errorIndex and varBindTable[-1][int(errorIndex)-1] or '?'
                )
        # else:
        #     for varBindTableRow in varBindTable:
        #         for name, val in varBindTableRow:
    return varBindTable

#Funkcja sprawdza czy urzadzenie jest osiagalne
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

#Klasa do polaczenia ssh
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
                cmdgen.UdpTransportTarget((SNMP_HOST_FT, SNMP_PORT)),
                '1.3.6.1.4.1.989.1.21.1.3.6.1.15.1'
            )
            for name, val in varBinds:
                logging.info(val.prettyPrint())
                return str(val.prettyPrint())

def createClient(q, server_ip, port,duration, reverse = False):
    result_d = {}
    client = iperf3.Client()
    client.duration = duration
    client.server_hostname = server_ip
    client.port = port
    client.reverse = reverse
    # client.json_output = False
    result = client.run()
    # print "wyniki przeplywnosci:"
    # print result.sent_Mbps
    if reverse == False :
        # print "reverse == False"
        q.put({'UL':result.sent_Mbps})
    else:
        q.put({'DL': result.sent_Mbps})
        # print "reverse == True"

file_r = open(RESULTS_PATH, "w")  # tworzenie pliku wynikowego
file_r.write("Attenuation;RSSI Avg;RSSI Ant 0;RSSI Ant 1;DL TP;UL TP;"
             "256qam56 DL;256qam34 DL;64qam56 DL;64qam34 DL;64qam23 DL;64qam12 DL;16qam34 DL;16qam12 DL;qpsk34 DL;qpsk12 DL;"
            "256qam56 UL;256qam34 UL;64qam56 UL;64qam34 UL;64qam23 UL;64qam12 UL;16qam34 UL;16qam12 UL;qpsk34 UL;qpsk12 UL;"
             )
file_r.close()

setRootLogger()  # utoworzenie root Loggera, teraz zamiast print należy pisać logging.debug('

#sprawdzenie czy wszystkie urzadzenia sa osiagalne- nie jest to wymagane
logging.info("Ping to FT: %r"%pingHost(SNMP_HOST_FT))
logging.info("Ping to FB: %r"%pingHost(SNMP_HOST_FB))
logging.info("Ping to remote server IP: %r"%pingHost(REMOTE_SERVER_IP))

connection = ''
if pingHost(REMOTE_IP):                                     #połączenie sie do serwera zdalnego i utworzenie demonow iperf3 -s
    logging.info("Remote server available")
    connection = ssh(REMOTE_IP, USERNAME, PASSWORD)         # utworzenie obiektu ssh
    connection.openShell()                                  # odpalanie indywidualnej powloki aby byla mozliwosc wprowadzania kilku komend nastepujacych po sobie
    connection.sendShell("iperf3 -s -D -p %i"%REMOTE_PORT_1)
    logging.info("Iperf3 daemon sever 1 initialized on port: %i"%REMOTE_PORT_1)
    time.sleep(1)
    connection.sendShell("iperf3 -s -D -p %i" % REMOTE_PORT_2)
    logging.info("Iperf3 daemon sever 2 initialized on port: %i" % REMOTE_PORT_2)
    # connection.closeConnection()
else:
    logging.info("Remote server unavailable")
    time.sleep(1)

connection.setRootAccount()
connection.sendShell('cd %s'%PATH_ATT_APP)
logging.info('Go to proper att app direcotry')

for att in range(0, 64):
    connection.sendShell('./setAtten %i'%(att*4))
    logging.info('Attenuation is set to %idB'%att)
    time.sleep(60)

    rssi = rssiStatus(snmpRssiQuery())

    #utworzenie obiektow ktore beda przechowywaly statystyki przed i po wykonaniu testu przeplywnosci
    beforeStats = StatsSlots()
    afterStats = StatsSlots()
    beforeStats.updateStatistics(snmpStatsQuery())



    if (checkNetEntryState((SNMP_HOST_FT), SNMP_COMMUNITY, SNMP_PORT, False) == 'RegistrationComplete'):
        q = multiprocessing.Queue()
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

        afterStats.updateStatistics(snmpStatsQuery())
        # print afterStats.stats_dl_slots
        comapreObject = ComparisonStats(beforeStats,afterStats)
        comapreObject.compareDLstats()
        comapreObject.compareULstats()
        rssi.rssiStatusUpdate(snmpRssiQuery())

#zapisanie wynikow do plikku
        file_r = open(RESULTS_PATH, "a")  # dodanie wynikow DL i UL
        file_r.write("\n%i;%i;%i;%i;%f;%f;" % (att,rssi.rssi_d['rssi_avg'],rssi.rssi_d['rssi_ant_0'],rssi.rssi_d['rssi_ant_1'],x['DL'], x['UL']))
        file_r.write("%f;%f;%f;%f;%f;%f;%f;%f;%f;%f;"%(comapreObject.stats_dl_per['256qam56'],
                                                      comapreObject.stats_dl_per['256qam34'],
                                                      comapreObject.stats_dl_per['64qam56'],
                                                      comapreObject.stats_dl_per['64qam34'],
                                                      comapreObject.stats_dl_per['64qam23'],
                                                      comapreObject.stats_dl_per['64qam12'],
                                                      comapreObject.stats_dl_per['16qam34'],
                                                      comapreObject.stats_dl_per['16qam12'],
                                                      comapreObject.stats_dl_per['qpsk34'],
                                                      comapreObject.stats_dl_per['qpsk12']
                                                      ))
        file_r.write("%f;%f;%f;%f;%f;%f;%f;%f;%f;%f"%(comapreObject.stats_ul_per['256qam56'],
                                                      comapreObject.stats_ul_per['256qam34'],
                                                      comapreObject.stats_ul_per['64qam56'],
                                                      comapreObject.stats_ul_per['64qam34'],
                                                      comapreObject.stats_ul_per['64qam23'],
                                                      comapreObject.stats_ul_per['64qam12'],
                                                      comapreObject.stats_ul_per['16qam34'],
                                                      comapreObject.stats_ul_per['16qam12'],
                                                      comapreObject.stats_ul_per['qpsk34'],
                                                      comapreObject.stats_ul_per['qpsk12']
                                                      ))
        file_r.close()

    else:
        logging.error('FT is not connected to FB')
        exit(1)

connection.closeConnection()
# for att in range(0, 64):
#     print att



# print beforeStats.stats_dl_slots
# # print firstStats.stats_ul_slots
# time.sleep(20)


# x = snmpRssiQuery()
# rssi = rssiStatus(snmpRssiQuery())
# time.sleep(10)
# rssi.rssiStatusUpdate(snmpRssiQuery())
# print rssi.checkRegistrationState()