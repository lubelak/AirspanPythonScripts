# -*- coding: utf-8 -*-

import requests
import time
import logging
# from lxml import html
# from selenium import webdriver
# import selenium


#### Metoda z użyciem selenium ####
# driver = webdriver.Firefox()
# driver.get(login_url)
#
# # username = driver.find_element_by_id('username')
# password = driver.find_element_by_id('passwd')
# password.send_keys('admin')
#
# driver.find_element_by_id('btn_login').click()
# # driver.get(overview_url)
# # rsrp = driver.find_element_by_id('identity_boardName')
# rsrp = driver.find_element_by_id('identity_boardName').text
# print rsrp

class KztechScraper():
    def __init__(self, ue_ip):
        self.payload = payload = {'username': 'admin',
                                  'passwd': 'admin',
                                  'submit_button': 'login',
                                  'submit_type': 'do_login',
                                  'change_action': 'gozila_cgi'
                                  }
        self.ue_ip = ue_ip
        self.login_url = 'http://' + ue_ip + '/apply.cgi'
        self.overview_url = 'http://' + ue_ip + '/lte/Overview_Ref.asp'
        self.session_requests = None
        self.overview_dict = {}

    def connnect(self):
        self.session_requests = requests.session()
        result = self.session_requests.post(self.login_url, data=self.payload)
        if result.text == 'success':
            logging.info('Login to KZ Tech page completed successfully')
        else:
            logging.error('Login to KZ Tech page FAILED')

    def getOverview(self):
        result = self.session_requests.get(self.overview_url, headers=dict(referer=self.overview_url))
        if result.status_code == 200:
            logging.info('Overview info was successufully downloaded')
            return result
        else:
            logging.error('Could not download the overview file')

    def parseOverview(self, overview_obj):
        overview_str = str(overview_obj.text)
        overview_list = overview_str.split(';')
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



# kztech = KztechScraper('10.70.25.59')
# kztech.connnect()
# print kztech.getLteInfo()
# time.sleep(20)
# print kztech.getLteInfo()




