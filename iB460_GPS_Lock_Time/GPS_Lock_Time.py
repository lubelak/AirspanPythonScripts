# -*- coding: utf-8 -*-
import paramiko
import os
import platform
import time
import re

# IP = '10.18.0.210'
IP = 'fe80::c6ed:baff:fea3:0482%eno1'
#USERNAME = 'admin'
#PASSWORD = 'HeWGEUx66m=_4!ND'
USERNAME = 'root'
PASSWORD = 'bsroot'
BOOT_TIME = 100                         #
MAX_REBOOT_COUNTER = 100                 #ile rebootow/powtorzen ma wykonac skrypt
MAX_CHECK_LOCK = 10                     #ile maksymalnie sekund skrypt ma sprawdzac ze iB460 ze zalockowany do gps przed rebootem
IF_LOCK_TIMER = 10                      #ile minut skrypt daje urzadzeniu na zalokowanie sie do gpsa, po tym czasie nastepuje reboot
RESULTS_PATH = "/home/airspan/Desktop/Results.csv"


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
    print "Ping command: ", comm
    response = os.popen(comm)  # otwarcie pipe z komendą do pingowania wybranego adresu
    for line in response.readlines():  # wczytanie całej odpowiedzi (do EOF) jako listy poszczególnych linii
        if (line.count("Reply") or line.count(
                "ttl")):  # sprawdzenie czy poszczególne linie zawierają słówko TTL (dla Windowsa) i ttl (dla Linuxa), jeśli tak oznacz to że jest odpowiedź od hosta.
            print line.strip()  # Metoda Count() zwraca ile razy słowo występuje w liście
            # print ip, "--> Live"
            response.close()
            return True
            break
    print "No response from host: ", ip
    return False


def get_gps_stat():
    reboot_counter = 0
    while True:
        if ping_host(IP):
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(IP, username=USERNAME, password=PASSWORD, look_for_keys=False, allow_agent=False)
            print "SSH connection established to %s" % IP
            client = client.invoke_shell()
            # print "Interactive SSH session established"
            # output = client.recv(1000)
            # print output
            client.send("\n")
            client.send("reboot\n")
            reboot_counter += 1
            time.sleep(1)
            output = client.recv(1000)
            # print output
            # print type(output)
            if output.find('The system is going down for reboot'):
                print "Rebooting..."
                print "Reboot Counter: ", reboot_counter
            if reboot_counter >= MAX_REBOOT_COUNTER:
                print "Test completed"
                print "Reboot Counter: ", reboot_counter
                break

            time.sleep(120)
        else:
            time.sleep(10)


class ssh:
    client = None
    shell = None

    def __init__(self, address, username, password):
        print "Connecting to server"
        self.client = paramiko.client.SSHClient()  # Utworzenie notwego klienta SSH
        self.client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())  # sprawia że paramiko podczas  łączenia ignoruje komunikat o nieznanym kluczu hosta i automatycznie go zatwierdza (przeważnie wymagane podczas pierwszego połączenia
        try:
            self.client.connect(address, username=username, password=password, look_for_keys=False, allow_agent=False)
        except (socket.error, paramiko.AuthenticationException, paramiko.SSHException) as message:
            print "Error: SSH connection to " + address + " failed: " +str(message)
            exit(1)

    def closeConnection(self):
        if (self.client != None):
            self.client.close()
            print "SSH connection has been terminated"

    def openShell(self):
        self.shell = self.client.invoke_shell()

    def sendCommand(self, command):
        if (self.client):
            stdin, stdout, stderr = self.client.exec_command(command)                   #wykorzystujac exec_command jest otwierana nowa powloka (shell) wiec nie da rady zmienic uzytkownika z admin na root, potrzeba utworzyc osobna powloke
            out = stdout.read()
            print out
        else:
            print("Connection not opened.")

    def sendShell(self, command):
        if (self.shell):
            self.shell.send(command + "\n")
        else:           print("Shell not opened.")

    def readShell(self):
        i = 0
        while not self.shell.recv_ready():                                              #Wait for the server to read and respond
            time.sleep(0.1)
            if i < 20:
                pass
            else:
                print "Empty buffer"
                break
            i = i + 1

        time.sleep(1)                                                                 #wait enaough for writing to (hopefully) be finishe
        if self.shell.recv_ready():
            result = self.shell.recv(9999)                                                     #read in
        else:
            print "Still buffer is empty"
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


def findGpsInfo(inputData):
    dict = {'numVisibleSatellites': '',
            'numTrackedSatellites': '',
            'uct': '',
            'date': '',
            'cNoRatio': '',
           'snrStatus': '',
            'lockStatus': '',
            'gpggaLockLostCounter': ''
            }

    lines = inputData.splitlines()                      #Podzielenie stringu wejsciowego na linie

    for line in lines:
        line = line.replace(' ', '')                    #usuniecie spacji
        #repr(line).replace(' ','d')
        #print line
        #match = re.search(r'(lockStatus\(16\)=)(\d)', line)
        if re.search(r'(numVisibleSatellites\(6\)=)(\d+)', line):                   #sprawdzenie dopasowań i wpisanie odpowiednich wartosci do slownika
            match = re.search(r'(numVisibleSatellites\(6\)=)(\d+)', line)
            dict['numVisibleSatellites'] = match.group(2)
        elif re.search(r'(numTrackedSatellites\(7\)=)(\d+)', line):
            match = re.search(r'(numTrackedSatellites\(7\)=)(\d+)', line)
            dict['numTrackedSatellites'] = match.group(2)
        elif re.search(r'(uct\(11\)=)(\d+)', line):
            match = re.search(r'(uct\(11\)=)(\d+)', line)
            dict['uct'] = match.group(2)
        elif re.search(r'(date\(12\)=)(\d+)', line):
            match = re.search(r'(date\(12\)=)(\d+)', line)
            dict['date'] = match.group(2)
        elif re.search(r'(cNoRatio\(13\)=)(\d+)', line):
            match = re.search(r'(cNoRatio\(13\)=)(\d+)', line)
            dict['cNoRatio'] = match.group(2)
        elif re.search(r'(snrStatus\(14\)=)(\d+)', line):
            match = re.search(r'(snrStatus\(14\)=)(\d+)', line)
            dict['snrStatus'] = match.group(2)
        elif re.search(r'(lockStatus\(16\)=)(\d)', line):
            match = re.search(r'(lockStatus\(16\)=)(\d)', line)
            dict['lockStatus'] = match.group(2)
        elif re.search(r'(gpggaLockLostCounter\(34\)=)(\d+)', line):
            match = re.search(r'(gpggaLockLostCounter\(34\)=)(\d+)', line)
            dict['gpggaLockLostCounter'] = match.group(2)
        else:
            pass
    #print dict
    return dict

def gpsLockTime():
    reboot_counter = 0
    reboot_time = 0.0
    lock_time = 0.0
    file_r = open(RESULTS_PATH, "w")
    file_r.write("RebootNumber;STATUS;TIME\n")
    lock_flag = False
    reboot_f = False
    tnet_f = False
    board_f = False
    start_time = time.time()

    while True:
        tnet_resp = 0
        lock_flag = False
        tnet_f = False
        board_f = False
        tnet_counter = 0
        board_counter = 0
        if pingHost(IP):
            if reboot_f == True:
                start_time = time.time()                                #czas pierwszej odpowiedzi na ping, czas uruchomienia się urządzenia
            connection = ssh(IP, USERNAME, PASSWORD)                #utworzenie obiektu ssh
            connection.openShell()                                  #odpalanie indywidualnej powloki aby byla mozliwosc wprowadzania kilku komend nastepujacych po sobie
            connection.sendShell("cd /bs")                          #przejscie do odpowiedniego folderu i uruchominie tneta
            output = connection.readShell()                         #czytanie z bufora tak aby po wprowadzeniu komendy w buforze nie bylo jakis smieci
            connection.sendShell("./tnet")
            print "./tnet command"
            output = connection.readShell()
            while output.find("Connected to DGS server") == -1:
                print "Waiting for tnet"
                time.sleep(1)
                output=connection.readShell()
                # tnet_counter += 1
                # print output
            print "Connected to DGS server"
            time.sleep(1)
            connection.sendShell("context set board")
            output = connection.readShell()
            while (output.find("[board] tnet > ") == -1):
                print "Waiting for context set board"
                connection.sendShell("")
                time.sleep(1)
                output=connection.readShell()
                board_counter += 1
                if board_counter >= 10:
                    print "Too long for respnose from board. New shell needed."
                    break
                # print output
            if (output.find("[board] tnet > ") != -1):
                print "context set board"
                time.sleep(1)
                board_f = True
            else:
                board_f = False
            if board_f == True:
                while (time.time() - start_time) <= (IF_LOCK_TIMER*60):
                    print "Time from first ping response: %s"% time.strftime("%H:%M:%S", time.gmtime(time.time() - start_time))
                    connection.sendShell("get -vv 9")  # komenda z prosba o wyswietlenie tablicy dotyczacej statusu gps
                    output = connection.readShell()  # czytanie bufora
                    #print output
                    dict_result = findGpsInfo(output)  # parsowanie na słownik wynikow ktore mnie interesuja
                    if dict_result['lockStatus']=='':
                        print "tnet not responding..."
                        tnet_resp = tnet_resp +1
                        if tnet_resp == 3:
                            print "tnet not responding %i times"%tnet_resp
                            print "new shell needed"
                            reboot_f = False
                            break
                    print dict_result  # wyswietlenie slownika
                    if dict_result['lockStatus'] == '1':
                        lock_time = time.time()
                        print "iB460 is locked"
                        time.sleep(2)
                        i = 1
                        while i <= (MAX_CHECK_LOCK):
                            connection.sendShell("get -vv 9")
                            output = connection.readShell()
                            dict_result = findGpsInfo(output)
                            if dict_result['lockStatus'] == '1':
                                print "iB460 is locked after: %ds"% i
                                time.sleep(1)
                                i=i+1
                                if i == (MAX_CHECK_LOCK):
                                    lock_flag = True
                            else:
                                print "iB460 lost gps after: %ds"% i
                                print "Timer start from beginning"
                                break
                        if lock_flag == True:
                            if reboot_counter != 0:
                                elapsed_time = lock_time - reboot_time
                                print "iB460 performed lock to gps after: "
                                print time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
                                # file_r.write("iB460 performed gps lock after: ")
                                file_r.write("OK;")
                                file_r.write(time.strftime("%H:%M:%S \n", time.gmtime(elapsed_time)))
                            if reboot_counter != MAX_REBOOT_COUNTER:
                                connection.sendShell("quit")
                                connection.sendShell("reboot")
                                print "reboot command"
                                reboot_f = True
                                reboot_counter = reboot_counter + 1
                                file_r.write("%i;" % reboot_counter)
                                print "Reboot number: %i \n" % reboot_counter
                                reboot_time = time.time()
                                print "Waiting for reboot (70s)"
                                time.sleep(70)
                                connection.closeConnection()
                                break
                            else:
                                reboot_counter = reboot_counter + 1
                                connection.closeConnection()
                                break
                    else:
                        print "ib460 isn't locked"
                        #connection.closeConnection()
                        time.sleep(5)
                else:
                    file_r.write("FAIL (TIMEOUT);\n")
                    if reboot_counter != MAX_REBOOT_COUNTER:
                        connection.sendShell("quit")
                        connection.sendShell("reboot")
                        print "reboot command"
                        reboot_f = True
                        reboot_counter = reboot_counter + 1
                        file_r.write("%i;" % reboot_counter)
                        reboot_time = time.time()
                        print "Waiting for reboot (70s)"
                        time.sleep(70)
                        connection.closeConnection()
                    else:
                        reboot_counter = reboot_counter + 1
                        connection.closeConnection()


                '''
                reboot_counter+=1
                time.sleep(1)
                output = client.recv(1000)
                #print output
                #print type(output)
                if output.find('The system is going down for reboot'):
                    print "Rebooting..."
                    print "Reboot Counter: ", reboot_counter
                    '''
        else:
            time.sleep(1)
        if reboot_counter == (MAX_REBOOT_COUNTER + 1):
            print "Test completed"
            print "Reboot Counter: %i"% (reboot_counter-1)
            file_r.close()
            exit(0)


gpsLockTime()



# #print time.strftime("%H:%M:%S", time.gmtime(elapsed_time))                             # ładny zapis czasu jaki upłynął
# #print time.strftime("%c")                                                               #aktualny czas

