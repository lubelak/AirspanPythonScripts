# -*- coding: utf-8 -*-

import paramiko
import logging
import socket
import time



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