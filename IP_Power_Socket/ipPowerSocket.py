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

#Do listwy nie ma dostepu po ssh
# REMOTE_IP = '10.4.0.36'               #dane do logowania po ssh do serwera
# USERNAME = 'admin'
# PASSWORD = 'admin'

SNMP_PUBLIC_COMMUNITY = 'public'               #dane do snmp
SNMP_PRIVATE_COMMUNITY = 'private'
SNMP_PORT = 161
SNMP_HOST = '10.4.0.36'             #adres IP Power Socket

MAIN_LOG_PATH = '/home/airspan/Desktop/PythonResults/IP_Power_Socket/MainLogIP.log'

TIMEOUT = 180                       #czas testu w sekundach

#Gniazda ktore beda braly udzial w tescie
out_inv = { 'out0': True,
            'out1': False,
            'out2': False,
            'out3': False,
            'out4': True
}

#Czas pracy poszczegolnego gniazda w sekundach
out_up_time = { 'out0': 40,
                'out1': 120,
                'out2': 180,
                'out3': 240,
                'out4': 60
}

#Czas uspienia/wylaczenia
out_sleep_time = {'out0': 20,
                  'out1': 120,
                  'out2': 180,
                  'out3': 240,
                  'out4': 30
}

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
        cmdgen.CommunityData(SNMP_PRIVATE_COMMUNITY),
        cmdgen.UdpTransportTarget((SNMP_HOST, SNMP_PORT)),
        (oid_table[out], rfc1902.Integer(0))
    )
    logging.info('Turn on: %s'%out)

#funkcja wylaczajaca gniazdo
def snmpTurnOffOut(out):
    errorIndication, errorStatus, errorIndex, \
    varBinds = cmdgen.CommandGenerator().setCmd(
        cmdgen.CommunityData(SNMP_PRIVATE_COMMUNITY),
        cmdgen.UdpTransportTarget((SNMP_HOST, SNMP_PORT)),
        (oid_table[out], rfc1902.Integer(1))
    )
    logging.info('Turn off: %s'%out)


#funkcja sprawdzajaca status gniazda, True znaczy włączone, False wyłączone
def snmpCheckOut(out):
    errorIndication, errorStatus, errorIndex, \
    varBinds = cmdgen.CommandGenerator().getCmd(
        cmdgen.CommunityData(SNMP_PUBLIC_COMMUNITY),
        cmdgen.UdpTransportTarget((SNMP_HOST, SNMP_PORT)),
        oid_table[out]
    )
    for name, val in varBinds:
        if val==0:
            logging.info('%s status: ON'%out)
            return True
        else:
            logging.info('%s status: OFF'%out)
            return False

#funkcja wlaczajaca wszystkie gniazda- stan poczatkowy
def snmpTurnOnAllOuts():
    for oid_key in oid_table:
        errorIndication, errorStatus, errorIndex, \
        varBinds = cmdgen.CommandGenerator().setCmd(
            cmdgen.CommunityData(SNMP_PRIVATE_COMMUNITY),
            cmdgen.UdpTransportTarget((SNMP_HOST, SNMP_PORT)),
            (oid_table[oid_key], rfc1902.Integer(0))
        )
        logging.info('Turn on: %s'%oid_key)
        # time.sleep(1)

#funkcja wlaczajaca i wylaczajaca gniazdo po odpowiedniej liczbie sekund zdefiniowanej w slownikach na poczatku skryptu
def snmpScheduler(out):
    while True:
        time.sleep(out_up_time[out])    #odczekanie odpowiedniej liczby sekund jaka ma byc wlaczone gniazdo
        snmpTurnOffOut(out)             #wylaczenie gniazda
        time.sleep(out_sleep_time[out]) #liczba sekund przez jaka ma byc wylaczone gniazdo
        snmpTurnOnOut(out)              #uruchomienie gniazda




setRootLogger()  # utoworzenie root Loggera, teraz zamiast print należy pisać logging.debug('
if pingHost(SNMP_HOST):
    logging.info("IP Power Socket is reachable")
else:
    logging.info("No response from IP Power Socket")

#wlaczenie wszystkich gniazd
snmpTurnOnAllOuts()

#sprawdzenie czy wszystkie gnaizda są włączone
for out_k in oid_table:
    snmpCheckOut(out_k)

#uruchomienie schedulera tylko dla tych gniazd oznaczonych jako True w out_inv
jobs = []
for out_key in out_inv:
    if out_inv[out_key] == True:
        logging.info('Turning on scheduler for: %s'%out_key)
        p = multiprocessing.Process(target=snmpScheduler, args=(out_key,), name=out_key)
        jobs.append(p)
        p.start()

time.sleep(TIMEOUT)

for j in jobs:
    logging.info("Scheduler for %s terminated"%j.name)
    j.terminate()


