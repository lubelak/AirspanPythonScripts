# -*- coding: utf-8 -*-
import logging
import socket
import multiprocessing
import threading
import paramiko
import os
import errno
import results
import time
from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.proto import rfc1902
from ssh import ssh
from ping import pingHost
from logger import setRootLogger
from readINI import readOption, readSection
import serial

# #Dane snmp dla listwy zasilającej
# SNMP_PUBLIC_COMMUNITY_POWER_SOCKET = 'public'               #dane do snmp
# SNMP_PRIVATE_COMMUNITY_POWER_SOCKET = 'private'
# SNMP_PORT_POWER_SOCKET = 161
# SNMP_HOST_POWER_SOCKET = '10.11.4.72'             #adres IP Power Socket


#Dane snmp dla iB460 FT
# SNMP_COMMUNITY_FT = 'public'               #dane do snmp
# SNMP_PORT_FT = 161
# SNMP_HOST_FT = '192.168.0.111'             #adres lokalny FT, po IPv6 nie mozna bylo pobrac informacji po snmp
# SNMP_HOST6_FT = 'fe80::c6ed:baff:fea3:0482'

#dane do ssh iB460
# LOCAL_USER = 'admin'
# LOCAL_PASSWORD = 'HeWGEUx66m=_4!ND'

# #sciezka gdzie zapisywane sa logi
# MAIN_LOG_PATH = './MainLogIP.log'
#
# #plik wynikowy
# RESULTS_PATH = './WarmScanList_results.csv'
# LOG_PATH = './Logs/LogReboot'                                  #log serialowy z FT


# SERIAL_PORT = '/dev/ttyUSB0'
# SERIAL_BAUDRATE = 115200



#TIMEOUT = 500000                      #czas testu w sekundach

# #liczba rebootow, w tym przypadku cold reboot poprzez odlaczenie zasilania
# MAX_REBOOT_COUNTER = 500
#
# #ile minut ft ma na rejestracje
# MAX_REG_TIMER = 20

#gniazdo które bierze udzial w tescie
out_inv = 'out0'

oid_table = {'out0': '.1.3.6.1.4.1.17095.3.1.0',
             'out1': '.1.3.6.1.4.1.17095.3.2.0',
             'out2': '.1.3.6.1.4.1.17095.3.3.0',
             'out3': '.1.3.6.1.4.1.17095.3.4.0',
             'out4': '.1.3.6.1.4.1.17095.3.5.0'
             }




#funkcja wlaczajaca gniazdo
def snmpTurnOnOut(out):
    errorIndication, errorStatus, errorIndex, \
    varBinds = cmdgen.CommandGenerator().setCmd(
        cmdgen.CommunityData(readOption('snmp_private_community_power_socket')),
        cmdgen.UdpTransportTarget((readOption('snmp_host_power_socket'), readOption('snmp_port_power_socket', True))),
        (oid_table[out], rfc1902.Integer(0))
    )
    logging.info('Turn on: %s' % out)

#funkcja wylaczajaca gniazdo
def snmpTurnOffOut(out):
    errorIndication, errorStatus, errorIndex, \
    varBinds = cmdgen.CommandGenerator().setCmd(
        cmdgen.CommunityData(readOption('snmp_private_community_power_socket')),
        cmdgen.UdpTransportTarget((readOption('snmp_host_power_socket'), readOption('snmp_port_power_socket'))),
        (oid_table[out], rfc1902.Integer(1))
    )
    logging.info('Turn off: %s' % out)



#funkcja usuwająca plik WarmScanList z FT
def deleteWarmScanListFile():
    connection = ssh(readOption('snmp_host_ft'), readOption('local_user'), readOption('local_password'))  # utworzenie obiektu ssh
    connection.openShell()  # odpalanie indywidualnej powloki aby byla mozliwosc wprowadzania kilku komend nastepujacych po sobie
    connection.sendShell("sudo rm /config/ft/sysdata.pdb")
    time.sleep(1)
    connection.sendShell("%s" % (readOption('local_password')))
    time.sleep(1)
    logging.info("WarmScanList file has been deleted")
    connection.closeConnection()

#funkcja sprawdzajaca w jakim stanie aktualnie znajduje sie ft
def checkNetEntryState(ip, community, port, ipv6 = False):
    if pingHost(ip):
        if ipv6 :
            errorIndication, errorStatus, errorIndex, \
            varBinds = cmdgen.CommandGenerator().getCmd(
                cmdgen.CommunityData(readOption('snmp_community_ft')),
                cmdgen.Udp6TransportTarget((readOption('snmp_host6_ft'), readOption('snmp_port_ft'))),
                '1.3.6.1.4.1.989.1.21.1.3.6.1.15.1'
            )
            for name, val in varBinds:
                logging.info(val.prettyPrint())
                return str(val.prettyPrint())
        else:
            errorIndication, errorStatus, errorIndex, \
            varBinds = cmdgen.CommandGenerator().getCmd(
                cmdgen.CommunityData(readOption('snmp_community_ft')),
                cmdgen.UdpTransportTarget((readOption('snmp_host_ft'), readOption('snmp_port_ft'))),
                '1.3.6.1.4.1.989.1.21.1.3.6.1.15.1'
            )
            for name, val in varBinds:
                logging.info(val.prettyPrint())
                return str(val.prettyPrint())

def constReadSerialToFile( stop_event, reboot_nr):
    log_path = readOption('log_path')
    if not os.path.exists(os.path.dirname(log_path)):
        try:
            os.makedirs(os.path.dirname(log_path))
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise

    file_log_name = '%s_%i.log' % (log_path, reboot_nr + 1)
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

def downloadLogs(reboot_nr):
    log_path = readOption('log_path')
    #print log_path
    log_path_per_reboot = readOption('log_path')  + str(reboot_nr) + '/'
    #print log_path_per_reboot
    if not os.path.exists(os.path.dirname(log_path)):
        try:
            os.makedirs(os.path.dirname(log_path))
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise

    if not os.path.exists(os.path.dirname(log_path_per_reboot)):
        try:
            os.makedirs(os.path.dirname(log_path_per_reboot))
            logging.info('Directory %s has been created' % log_path_per_reboot)
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise
    local_pc_user = readOption('local_pc_user')
    local_pc_pass = readOption('local_pc_pass')
    local_pc_ip = readOption('local_pc_ip')
    connection = ssh(readOption('snmp_host_ft'), readOption('local_user'), readOption('local_password'))  # utworzenie obiektu ssh
    connection.openShell()  # odpalanie indywidualnej powloki aby byla mozliwosc wprowadzania kilku komend nastepujacych po sobie
    #print "scp -r /var/log %s@%s:%s" % (local_pc_user, local_pc_ip, log_path_per_reboot)
    connection.sendShell("scp -r /var/log %s@%s:%s" % (local_pc_user, local_pc_ip, log_path_per_reboot))
    time.sleep(1)
    connection.sendShell("y")
    time.sleep(1)
    #print connection.readShell()
    connection.sendShell("%s" % (local_pc_pass))
    logging.info('Downloading logs files')
    time.sleep(30)
    connection.closeConnection()



####  OD TEGO MIEJSCA STARTUJE SKRYPT  ####
def run():
    #utoworzenie root Loggera, teraz zamiast print należy pisać logging.info('
    main_log_path = readOption('main_log_path')
    setRootLogger(main_log_path)

    # Utworzenie pliku wynikowego
    res_csv = results.Results(readOption('results_path'))
    myHeaders = ['Reboot Number', 'Registration Time']
    res_csv.writeHeader(myHeaders)
    # utworzenie slownika ktory bedzie przechowywal tymczasowe wyniki
    result_dict = dict((k, '') for k in myHeaders)


    #sprawdzenie czy listwa jest pingowalna, nawet jesli nie jest to test leci dalej- brak czasu na obsluge bledow
    if pingHost(readOption('snmp_host_power_socket')):
        logging.info("IP Power Socket is reachable")
    else:
        logging.info("No response from IP Power Socket")

    #sprawdzenie czy FT jest pingowalne po interfejsie eth (internal) nie po radiowym (tap0)
    if pingHost(readOption('snmp_host_ft')):
        logging.info("FT is reachable")
    else:
        logging.info("No response from FT")

    #usunięcie pliku WarmScanList z FT
    deleteWarmScanListFile()

    # #czas dla mnie na weryfikacje czy faktycznie plik zostal usuniety

    time.sleep(120)


    power_on_time = 0       #czas wlaczenia zasilania
    reg_compl_time = 0      #czas po ktorym zarejestrowalo sie urzadzenie
    elapsed_time = 0        #czas jaki uplynal
    max_reboot_counter = readOption('max_reboot_counter', True)
    print max_reboot_counter
    #glowna petla
    for i in range(max_reboot_counter):
        snmpTurnOffOut(out_inv)        #wylaczenie gniazda
        time.sleep(5)
    
    #     #uruchominie watku logowania serialowego
    #     stop_thread = threading.Event()
    #     thread = threading.Thread(target=constReadSerialToFile, args=(stop_thread, i)).start()
        snmpTurnOnOut(out_inv)         #wlaczenie gniazda
        power_on_time = time.time()     #zapis czasu
        logging.info("waiting 60s ")    #odczekanie az urzadzenie sie uruchomi
        time.sleep(60)
        while (time.time() - power_on_time) <= (readOption('max_reg_timer', True) * 60):
            currentNetState = checkNetEntryState((readOption('snmp_host_ft')), readOption('snmp_community_ft'), readOption('snmp_port_ft', True), False)
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
    result_dict['Reboot Number'] = i+1
    result_dict['Registration Time'] = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
    res_csv.writeDict(myHeaders, result_dict)
    #
    #     file_r = open(RESULTS_PATH, "a")  # dodanie liczby porzadkowej kazdego rebootu i czasu rejestracji
    #     file_r.write("\n%i;" % (i + 1))
    #     file_r.write(time.strftime("%H:%M:%S", time.gmtime(elapsed_time)))
    #     file_r.close()
    #
    #     #wylaczenie watku logowania serialowego
    #     stop_thread.set()
    #     time.sleep(1)
    downloadLogs(i+1)
    #logging.info("END OF SCRIPT")


if __name__ == '__main__':
    run()
