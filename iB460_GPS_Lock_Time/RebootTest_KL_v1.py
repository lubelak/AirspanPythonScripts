# -*- coding: utf-8 -*-
import paramiko
import os
import platform
import time



#IP = '10.18.0.210'
IP = 'fe80::c6ed:baff:fea3:a905%eno1'
USERNAME = 'admin'
PASSWORD = 'HeWGEUx66m=_4!ND'
BOOT_TIME = 100
MAX_REBOOT_COUNTER = 10


def reboot_host():
    reboot_counter = 0
    while True:
        if ping_host(IP):
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(IP, username=USERNAME, password=PASSWORD, look_for_keys=False, allow_agent=False)
            print "SSH connection established to %s" % IP
            client = client.invoke_shell()
            #print "Interactive SSH session established"
            #output = client.recv(1000)
            #print output
            client.send("\n")
            client.send("reboot\n")
            reboot_counter+=1
            time.sleep(1)
            output = client.recv(1000)
            #print output
            #print type(output)
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

def ping_host(ip):
    oper = platform.system()                                         # Sprawdzenie z jakim systemem operacyjnym mamy do czynienie
    if (oper == "Windows"):                                          # Jest to ważne w stosunku jakiej komendy ping mamy użyć
        #print "This is Windows system"
        ping1 = "ping -n 1 "
    elif (oper == "Linux" and ip[0]!="f"):
        #print "This is Linux system"
        ping1 = "ping -c 1 "
    elif (oper == "Linux" and ip[0]=="f"):
	ping1 = "ping6 -c 1  "
    else:
        print "Unknown operating system"
        #ping1 = "ping -c 1 "

    comm = ping1 + ip                                                 # utworzenie komendy jaka ma być wykonana w systemie
    print "Ping command: ", comm
    response = os.popen(comm)                                         # otwarcie pipe z komendą do pingowania wybranego adresu
    for line in response.readlines():                                 #wczytanie całej odpowiedzi (do EOF) jako listy poszczególnych linii
        if (line.count("Reply") or line.count(
                "ttl")):                                              #sprawdzenie czy poszczególne linie zawierają słówko TTL (dla Windowsa) i ttl (dla Linuxa), jeśli tak oznacz to że jest odpowiedź od hosta.
            print line.strip()                                               #Metoda Count() zwraca ile razy słowo występuje w liście
            #print ip, "--> Live"
            response.close()
            return True
            break
    print "No response from host: ", ip
    return False

reboot_host()
