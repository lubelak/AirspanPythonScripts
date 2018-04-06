# -*- coding: utf-8 -*-

import requests
import time
import logging
from ssh import ssh
import re

class KztechScraperRemote():
    def __init__(self, server_ssh_cred, script_path):
        self.server_ssh_cred = server_ssh_cred
        self.script_path = script_path
        self.server_ssh = None

        self.session_requests = None
        self.overview_dict = {}

    def connnect(self):
        self.server_ssh = ssh(self.server_ssh_cred['management_ip'], self.server_ssh_cred['username'],
                              self.server_ssh_cred['password'])  # utworzenie obiektu ssh
        self.server_ssh.openShell()  # odpalanie indywidualnej powloki aby byla mozliwosc wprowadzania kilku komend nastepujacych po sobie
        output = self.server_ssh.readShell()  # wczytujemy pierwsze śmieci po podłączeniu się po ssh
        # print output


    def getOverview(self):
        self.server_ssh.sendShell('python %s' % self.script_path)
        time.sleep(3)
        output = self.server_ssh.readShell()
        match = re.search(r'(KZ)(.*)(TM3)', output)
        return match.group()

    def parseOverview(self, overview_obj):
        # overview_str = str(overview_obj.text)
        overview_list = overview_obj.split(';')
        self.overview_dict['manufacturer'] = overview_list[0]
        self.overview_dict['model_name'] = overview_list[1]
        self.overview_dict['chip_model'] = overview_list[2]
        self.overview_dict['serial_number'] = overview_list[3]
        self.overview_dict['imei'] = overview_list[4]
        self.overview_dict['duplexing_scheme'] = overview_list[7]
        self.overview_dict['firmware_version'] = overview_list[8]

        self.overview_dict['ul_bandwidth'] = overview_list[12]
        self.overview_dict['dl_bandwidth'] = overview_list[13]
        self.overview_dict['ul_frequency'] = overview_list[14]
        self.overview_dict['dl_frequency'] = overview_list[15]
        self.overview_dict['connection_state'] = overview_list[16]
        self.overview_dict['sim_card_state'] = overview_list[17]
        self.overview_dict['signal_quality'] = overview_list[18]
        self.overview_dict['network_description'] = overview_list[19]
        self.overview_dict['imsi'] = overview_list[28]
        self.overview_dict['crnti'] = overview_list[31]
        self.overview_dict['pci'] = overview_list[32]
        self.overview_dict['ipv4_address'] = overview_list[38]
        self.overview_dict['ipv4_dns'] = overview_list[39]
        self.overview_dict['ipv6_address'] = overview_list[40]
        self.overview_dict['ipv6_dns'] = overview_list[41]
        self.overview_dict['cqi'] = overview_list[42]
        self.overview_dict['registered_plmn'] = overview_list[44]
        self.overview_dict['bearer_id'] = overview_list[45]
        self.overview_dict['qci'] = overview_list[47]
        self.overview_dict['transfer_mode'] = overview_list[49]
        #właściwe wartości dla rsrp, rssi itd.
        rsrp_str = overview_list[9]
        rsrp_list = rsrp_str.split(',')
        self.overview_dict['rsrp_0'] = float(rsrp_list[0])/100
        self.overview_dict['rsrp_1'] = float(rsrp_list[1]) / 100
        self.overview_dict['rssi'] = float(overview_list[10])/100
        self.overview_dict['sinr'] = float(overview_list[11])/100
        self.overview_dict['rsrq'] = float(overview_list[35])/100
        self.overview_dict['tx_power'] = float(overview_list[37])/100

        return self.overview_dict

    def getLteInfo(self):
        r = self.getOverview()
        return self.parseOverview(r)

# server_info = {'iperf_ip': '10.70.25.59',
#                'management_ip': '10.11.7.251',
#                'username': 'airspan',
#                'password': 'localadmin'
#                }
# path = '/home/airspan/kztechScraper_local.py'
#
# kztech = KztechScraperRemote(server_info, path)
# kztech.connnect()
# # output = kztech.getOverview()
# # match = re.search(r'(KZ)(.*)(TM3)', output)
# print kztech.getLteInfo()
#             # ue_radio_info = kztech.getLteInfo()