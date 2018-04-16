# -*- coding: utf-8 -*-


from ssh import ssh
import threading
import time
import logging
import os
import subprocess, sys
from subprocess import CREATE_NEW_CONSOLE


class IperfManager():
    def __init__(self, server_ssh_cred, ue_ip):
        self.server_ssh_cred = server_ssh_cred
        self.ue_ip = ue_ip

    ######do pointMeter ##########
    def performSingleDlUdpTest(self, bandwidth, time_sec=60, port_nr=5111, server_add_parameters='',
                               client_add_parameters=''):
        server_par = server_add_parameters + ' -u '
        client_par = client_add_parameters + (' -b%sM ' % bandwidth)
        return self.performSingleDlTest(time_sec, port_nr, server_par, client_par)

    def performSingleUlUdpTest(self, bandwidth, time_sec=60, port_nr=5111, server_add_parameters='',
                               client_add_parameters=''):
        server_par = server_add_parameters + ' -u '
        client_par = client_add_parameters + (' -b%sM ' % bandwidth)
        return self.performSingleUlTest(time_sec, port_nr, server_par, client_par)

    def performSingleDlTcpTest(self, parallel, time_sec=60, port_nr=5111, server_add_parameters='',
                               client_add_parameters=''):
        server_par = server_add_parameters
        client_par = client_add_parameters + (' -P%i ' % parallel)
        return self.performSingleDlTest(time_sec, port_nr, server_par, client_par)

    def performSingleUlTcpTest(self, parallel, time_sec=60, port_nr=5111, server_add_parameters='',
                               client_add_parameters=''):
        server_par = server_add_parameters
        client_par = client_add_parameters + (' -P%i ' % parallel)
        return self.performSingleUlTest(time_sec, port_nr, server_par, client_par)

    def performSingleDlTest(self, time_sec=60, port_nr=5111, server_add_parameters='',
                            client_add_parameters=''):
            client_command = 'iperf ' + (' -c %s ' % self.ue_ip) + \
                             (' -t%i ' % time_sec) + client_add_parameters + (' -p%i ' % port_nr)
            server_command = 'iperf -s -f m ' + (' -p%i ' % port_nr) + server_add_parameters
            logging.info('Client command: %s' % client_command)
            logging.info('Server command: %s' % server_command)
            # utworzenie serwera iperf
            local_server = IperfLocalServer(server_command)
            local_server.createServer()
            # event ktory konczy dodatkowy watek
            stop_thread = threading.Event()
            t1 = threading.Thread(target=local_server.readBuffer, args=(stop_thread,)).start()
            logging.info('DL local iperf server has been created')
            time.sleep(1)
            # utworzenie clienta iperf
            remote_client = IperfClient(self.server_ssh_cred, client_command)
            remote_client.createClient()
            logging.info('Client is running with command: %s' % client_command)
            # oczekiwanie na zakończenie testu +10s
            logging.info('Waiting for end of iperf test')
            time.sleep(time_sec + 10)
            remote_client.killClient()

            # odczyt wyników
            stop_thread.set()
            time.sleep(1)
            local_server.killServer()
            time.sleep(1)
            logging.info('Local iperf server has been killed')
            result = local_server.readReport()
            return result
    def performSingleUlTest(self, time_sec=60, port_nr=5111, server_add_parameters='',
                               client_add_parameters=''):
            client_command = 'iperf ' + (' -c %s ' % self.server_ssh_cred['iperf_ip']) + \
                             (' -t%i ' % time_sec) + client_add_parameters + (' -p%i ' % port_nr)
            server_command = 'iperf -s -f m ' + (' -p%i ' % port_nr) + server_add_parameters
            logging.info('Client command: %s' % client_command)
            logging.info('Server command: %s' % server_command)
            # utworzenie serwera iperf
            remote_server = IperfServer(self.server_ssh_cred, server_command)
            remote_server.createServer()
            logging.info('Remote iperf server is running with command: %s' % server_command)
            time.sleep(1)
            # utworzenie clienta iperf
            local_client = IperfLocalClient(client_command)
            local_client.createClient()
            logging.info('Local iperf client has been created')
            time.sleep(1)
            logging.info('Waiting for end of iperf test')
            time.sleep(time_sec + 10)
            local_client.killClient()

            result = remote_server.readReport()
            remote_server.killServer()
            return result



class IperfObject():
    def __init__(self, ssh_cred):
        self.ssh_cred = ssh_cred


class IperfClient(IperfObject):
    def __init__(self, ssh_cred, command):
        IperfObject.__init__(self, ssh_cred)
        self.command = command

    def createClient(self):
        self.client_ssh = ssh(self.ssh_cred['management_ip'], self.ssh_cred['username'], self.ssh_cred['password'])  # utworzenie obiektu ssh
        self.client_ssh.openShell()  # odpalanie indywidualnej powloki aby byla mozliwosc wprowadzania kilku komend nastepujacych po sobie
        output = self.client_ssh.readShell()  # wczytujemy pierwsze śmieci po podłączeniu się po ssh
        # print output
        self.client_ssh.sendShell(self.command)

    def killClient(self):
        self.client_ssh.closeConnection()



class IperfServer(IperfObject):
    def __init__(self, ssh_cred, command):
        IperfObject.__init__(self, ssh_cred)
        self.command = command

    def createServer(self):
        self.server_ssh = ssh(self.ssh_cred['management_ip'], self.ssh_cred['username'], self.ssh_cred['password'])  # utworzenie obiektu ssh
        self.server_ssh.openShell()  # odpalanie indywidualnej powloki aby byla mozliwosc wprowadzania kilku komend nastepujacych po sobie
        output = self.server_ssh.readShell()  # wczytujemy pierwsze śmieci po podłączeniu się po ssh
        # print output
        self.server_ssh.sendShell(self.command)

    def killServer(self):
        self.server_ssh.closeConnection()

    def readReport(self):
        """
        funkcja która czyta z shella. Od ostatniej linii sprawdza czy jest str [SUM] który świadczy że był to test udp.
        Jeśli nie ma to sprawdza czy jest info o Mbps- świadczy to o tym ze był to test udp lub tcp z jednym streamem.
        :return: osiagnieta przepływnośc
        """
        report = self.server_ssh.readShell()
        for line in reversed(report.splitlines()):
            # print line
            if '[SUM]' in line:
                logging.info('Line which contains throughput report: %s' % line)
                line_list = line.split(' ')
                value_index = None
                for i, x in enumerate(line_list):
                    if x == 'Mbits/sec':
                        value_index = i - 1
                # print value_index
                return line_list[value_index]
            elif 'Mbits/sec' in line:
                # print line
                logging.info('Line which contains throughput report: %s' % line)
                line_list = line.split(' ')
                value_index = None
                for i, x in enumerate(line_list):
                    if x == 'Mbits/sec':
                        value_index = i - 1
                # print value_index
                return line_list[value_index]
            else:
                pass
        # print report

def createBandwidthList(theo_rate, start_per = 70, stop_per = 140, step_per = 10):
    """Funkcja która zwraca tablice przeplywnosci ktore powinny byc
        spradzone podczas testu udp. Wartości co do 1 miejsca po przecinku.
    """
    rate_list = []
    for i in range(start_per, stop_per + step_per, step_per):
        rate_list.append(round((float(theo_rate) * i / 100), 1))
    return rate_list


################################# Klasy dla pointMeter  #######################
class IperfLocalClient():
    def __init__(self, command):
        self.command = command
        self.process_1 = None

    def createClient(self):
        self.process_1 = subprocess.Popen(self.command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        # self.process_1.wait()

    #to nie jest potrzebne, po wykonaniu polecenia iperf powłoka się zamyka
    def killClient(self):
        self.process_1.kill()




class IperfLocalServer():
    def __init__(self, command):
        # super(IperfLocalServer, self).__init__()
        self.command = command
        self.process_1 = None
        self.output = ''


    def createServer(self):
        self.process_1 = subprocess.Popen(self.command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        # self.process_1.communicate()
        # print 'iperf server created'
        logging.info('Iperf server created')

    def readBuffer(self, stop_event):
        self.output = ''
        # for line in iter(self.process_1.stdout.readline, b''):
        #     print(line.rstrip())
        while not stop_event.is_set():
            line = self.process_1.stdout.readline()
            self.output += line
            # print line
        else:
            logging.info('end of thread')


    def killServer(self):
        self.process_1.kill()

    def readReport(self):
        """
        funkcja która czyta z shella. Od ostatniej linii sprawdza czy jest str [SUM] który świadczy że był to test udp.
        Jeśli nie ma to sprawdza czy jest info o Mbps- świadczy to o tym ze był to test udp lub tcp z jednym streamem.
        :return: osiagnieta przepływnośc
        """
        report = self.output
        # print report
        for line in reversed(report.splitlines()):
            # print line
            if '[SUM]' in line:
                logging.info('Line which contains throughput report: %s' % line)
                line_list = line.split(' ')
                value_index = None
                for i, x in enumerate(line_list):
                    if x == 'Mbits/sec':
                        value_index = i - 1
                # print value_index
                return line_list[value_index]
            elif 'Mbits/sec' in line:
                # print line
                logging.info('Line which contains throughput report: %s' % line)
                line_list = line.split(' ')
                value_index = None
                for i, x in enumerate(line_list):
                    if x == 'Mbits/sec':
                        value_index = i - 1
                # print value_index
                return line_list[value_index]
            else:
                pass
        # print report

# cmd = 'iperf -s -u -p5111 '
# cmd2 = 'iperf -c10.70.22.101 -t10 -b10M '
# # p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
# # print p.stdout.readline()
# # print p.stdout.readline()
# # # p.communicate()[0]
# # # time.sleep(10)
# # print 'czytamy po 10s'
# #
# # for line in iter(p.stdout.readline, b''):
# #     print(line.rstrip())
#
# # client1 = IperfLocalClient(cmd2)
# # client1.createClient()
# server1 = IperfLocalServer(cmd)
# server1.createServer()
# # thread = threading.Thread(target=constReadSerialToFile, args=(stop_thread, i)).start()
# stop_thread = threading.Event()
# t1 = threading.Thread(target=server1.readBuffer, args=(stop_thread, )).start()
# # t1.daemon = True
# # t1.start()
# # t1.join()
# print 'sleeping 30s'
# time.sleep(30)
#
# stop_thread.set()
#
# time.sleep(2)
#
# server1.killServer()
# time.sleep(1)
# print 'kill iperf server'
# print server1.readReport()


# list_one = [1, 10, 5, 25, 30, 8]
# list_two = [8, 10, 7, 32, 33, 5]
# list_three = [x+y for x, y in zip(list_one, list_two)]
# print list_three
# print list_one.index(max(list_one))
#
# result_l = []
# result_l.sort()
# print('Final list of results: %s' % ('; '.join(map(str, result_l))))
# try:
#     print result_l[-1]
# except IndexError:
#     print 0
# b = 30.0
# a = 1.0
# print (str(b) + '+' + str(a))
