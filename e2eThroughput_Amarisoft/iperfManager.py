# -*- coding: utf-8 -*-


from ssh import ssh
import threading
import time
import logging

class IperfManager():
    def __init__(self, server_ssh_cred, client_ssh_cred):
        self.server_ssh_cred = server_ssh_cred
        self.client_ssh_cred = client_ssh_cred
        self.stop_event = threading.Event()

    def performDlUdpTest(self, bandwidth_l, time_sec=60, port_nr=5111, server_add_parameters='', client_add_parameters=''):
        return self.performUdpTest(bandwidth_l, True, time_sec, port_nr, server_add_parameters,
                       client_add_parameters)

    def performUlUdpTest(self, bandwidth_l, time_sec=60, port_nr=5111, server_add_parameters='', client_add_parameters=''):
        return self.performUdpTest(bandwidth_l, False, time_sec, port_nr, server_add_parameters,
                       client_add_parameters)

    def performDlTcpTest(self, parallel_l, time_sec=60, port_nr=5111, server_add_parameters='', client_add_parameters=''):
        return self.performTcpTest(parallel_l, True, time_sec, port_nr, server_add_parameters,
                       client_add_parameters)

    def performUlTcpTest(self, parallel_l, time_sec=60, port_nr=5111, server_add_parameters='', client_add_parameters=''):
        return self.performTcpTest(parallel_l, False, time_sec, port_nr, server_add_parameters,
                       client_add_parameters)

    def performUdpTest(self, bandwidth_l, reverse=False, time_sec=60, port_nr=5111, server_add_parameters='', client_add_parameters=''):
        if reverse:
            server_cred_tmp = self.client_ssh_cred
            client_cred_tmp = self.server_ssh_cred
        else:
            server_cred_tmp = self.server_ssh_cred
            client_cred_tmp = self.client_ssh_cred

        #pętla sprawdzająca TP udp
        result_list = []
        for bandwidth in bandwidth_l:
            #po to jest ten server adres bo do ip wykorzystujemy adres lokalny a wysyłamy ruch na adres wan/lte
            client_command = 'iperf ' + (' -c %s ' % server_cred_tmp['iperf_ip']) + (' -b%fM ' % bandwidth) + \
                             (' -t%i ' % time_sec) + client_add_parameters + (' -p%i ' % port_nr)
            server_command = 'iperf -s -u -f m ' + (' -p%i ' % port_nr) + server_add_parameters
            logging.info('Client command: %s' % client_command)
            logging.info('Server command: %s' % server_command)
            server_host =IperfServer(server_cred_tmp, server_command)
            server_host.createServer()
            logging.info('Iperf server is running with command: %s' % server_command)
            time.sleep(1)

            client_host = IperfClient(client_cred_tmp, client_command)
            client_host.createClient()
            logging.info('Client is running with command: %s' % client_command)
            # oczekiwanie na zakończenie testu +10s
            time.sleep(time_sec + 10)
            client_host.killClient()
            result = server_host.readReport()
            try:
                result_list.append(float(result))
                logging.info('Proper iperf report from server')
            except TypeError:
                logging.error('Improper report from iperf server. Time sleep 60s')
                time.sleep(60)
            logging.info('Temporary list of results: %s' % (';'.join(map(str, result_list))))
            server_host.killServer()

        result_list.sort()
        logging.info('Final list of results: %s' % ('; '.join(map(str, result_list))))
        return result_list[-1]

    def performTcpTest(self, parallel_l, reverse=False, time_sec=60, port_nr=5111, server_add_parameters='', client_add_parameters=''):
        if reverse:
            server_cred_tmp = self.client_ssh_cred
            client_cred_tmp = self.server_ssh_cred
        else:
            server_cred_tmp = self.server_ssh_cred
            client_cred_tmp = self.client_ssh_cred
        result_list = []
        for parallel in parallel_l:
            # po to jest ten server adres bo do ip wykorzystujemy adres lokalny a wysyłamy ruch na adres wan/lte
            client_command = 'iperf ' + (' -c %s ' % server_cred_tmp['iperf_ip']) + (' -P%i ' % parallel) + \
                             (' -t%i ' % time_sec) + (' -p%i ' % port_nr) + client_add_parameters
            server_command = 'iperf -s -f m ' + (' -p%i ' % port_nr) + server_add_parameters
            logging.info('Client command: %s' % client_command)
            logging.info('Server command: %s' % server_command)
            server_host = IperfServer(server_cred_tmp, server_command)
            server_host.createServer()
            logging.info('Iperf server is running with command: %s' % server_command)
            time.sleep(1)

            client_host = IperfClient(client_cred_tmp, client_command)
            client_host.createClient()
            logging.info('Client is running with command: %s' % client_command)
            #oczekiwanie na zakończenie testu +10s
            time.sleep(time_sec + 10)
            logging.info('Waiting for end of iperf test')
            client_host.killClient()
            result = server_host.readReport()
            try:
                result_list.append(float(result))
                logging.info('Proper report from iperf server')
            except TypeError:
                logging.error('Improper report from iperf server. Time sleep 60s')
                time.sleep(60)
            logging.info('Temporary list of results: %s' % (';'.join(map(str, result_list))))
            server_host.killServer()

        result_list.sort()
        logging.info('Final list of results: %s' % ('; '.join(map(str, result_list))))
        return result_list[-1]


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






