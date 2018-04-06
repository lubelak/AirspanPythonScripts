# -*- coding: utf-8 -*-

import logger
from iperfManager import IperfManager, createBandwidthList
from ping import pingHost
import logging
from nbi import Argstruct, nbi
import node
from nodeLogger import RelayLogger
import results
from kztechScraper import KztechScraper
# import multiprocessing
# import threading
import time
from readINI import readOption, readSection
from amarisoftManager import AmarisoftManager


def run():
    # ustawinie loggera
    main_log_path = readOption('main_log_path')
    logger.setRootLogger(main_log_path)

    # utworzenie obiektu informacji o wykonywanym teście
    test_config_info = results.TestConfigInfo(readOption('test_info_path'))
    test_config_info.writeTestName('e2e Throughput')
    test_config_info.writeStartTime()

    # wczytanie profili Amarisoftu
    amarisoft_profiles_dict, amarisoft_profiles_list = readSection('amarisoft_profiles')

    # wczytanie informacji o wezlach iperfowych
    ubuntu_iperf_dict, ubuntu_iperf_list = readSection('iperf_ubuntu_config')
    au_iperf_dict, au_iperf_list = readSection('au_config')
    ue_iperf_dict, ue_iperf_list = readSection('ue_config')

    #wczytanie ip amarisoft i spr czy jest osiagalne
    amarisoft_ip = readOption('amarisoft_ip')
    if pingHost(amarisoft_ip):
        logging.info('Ping respond from Amarisoft: %s', amarisoft_ip)
    else:
        logging.error('No response from Amarisoft: %s', amarisoft_ip)
        exit(1)

    # połączenie do amarisoftu
    amarisoft  = AmarisoftManager(amarisoft_ip, readOption('amarisoft_user'), readOption('amarisoft_pass'))  # utworzenie obiektu AmarisoftManager
    amarisoft.connect()

    # odczytanie adresu netspana
    netspan_ip = readOption('netspan_ip')

    # sprawdzenie czy Netspan jest dostępny
    if pingHost(netspan_ip):
        logging.info('Ping respond from Netspan: %s', netspan_ip)
    else:
        logging.error('No response from Netspan: %s', netspan_ip)
        exit(1)
    # utowrzenie obiektu do połączenia z netspanem i weryfikacja wersji Netspana
    netspan = nbi(netspan_ip,
                  readOption('netspan_sr'),
                  readOption('netspan_user'),
                  readOption('netspan_pass'))
    logging.info('Netspan version: %s', netspan.getNmsVersion())

    # utworzenie obiektu AU
    au = node.Node(readOption('node_name'))

    # pobranie i zapis informacji o urzadzeniu
    test_config_info.writeNodeInfo(netspan, readOption('node_name'))

    # Utworzenie pliku wynikowego
    res_csv = results.Results(readOption('result_path'))
    myHeaders = ['Amarisoft_Profile_Name', 'Relay_RSRP', 'Relay_RSSI',
                 'Relay_RSRQ', 'Relay_SINR', 'Relay_EARFCN',
                 'Relay_PCI', 'Relay_DL_UDP', 'Relay_UL_UDP', 'Relay_DL_TCP', 'Relay_UL_TCP',
                 'UE_RSRP_0', 'UE_RSRP_1', 'UE_RSRQ', 'UE_SINR',
                 'UE_FREQ', 'UE_PCI', 'UE_DL_UDP', 'UE_UL_UDP', 'UE_DL_TCP', 'UE_UL_TCP', 'STATUS']

    res_csv.writeHeader(myHeaders)
    # utworzenie slownika ktory bedzie przechowywal tymczasowe wyniki
    result_dict = dict((k, '') for k in myHeaders)

    # czas na stabilizacje połączenia
    establishment_time = readOption('establishment_time', True)

    #testowy fragment kodu
    # print au.enbRfStatusGet(netspan)

    # załadowanie właściwego profilu amarisoft
    for profile_item in amarisoft_profiles_list:
        for key, value in profile_item.iteritems():
            logging.info('Amarisoft profile: %s' % value)
            #określenie jaki profil jest aktualnie pobrany
            profile_list = value.split('/')
            result_dict['Amarisoft_Profile_Name'] = profile_list[-1]

            amarisoft.setProfile(value)
            logging.info('sleeping %s' % establishment_time)
            time.sleep(establishment_time)

            #sprawdzenie czy jest online i InService
            while True:
                try:
                    if (au.enbRfStatusGet(netspan)['OperationalStatus'][0] == 'InService' and
                               au.enbRfStatusGet(netspan)['OperationalStatus'][1] == 'InService' and
                           pingHost(au_iperf_dict['iperf_ip'])):
                        logging.info('Node is InService, waiting %s to stable connection' % establishment_time)
                        time.sleep(establishment_time)
                        break
                    else:
                        logging.error('Node is Out of Service')
                        time.sleep(5)
                except IndexError:
                    logging.error('enbRfStatusGet error, waiting for Node')
                    time.sleep(5)

            # informacje radiowe z relaya
            tnet = RelayLogger(au_iperf_dict['iperf_ip'], au_iperf_dict['username'], au_iperf_dict['password'])
            relay_radio_info = tnet.getRelayUeInfo()
            logging.info('Relay radio info: %s' % relay_radio_info)
            result_dict['Relay_RSRP'] = relay_radio_info['rsrp']
            result_dict['Relay_RSSI'] = relay_radio_info['rssi']
            result_dict['Relay_RSRQ'] = relay_radio_info['rsrq']
            result_dict['Relay_SINR'] = str(float(relay_radio_info['sinr']) / 100)
            result_dict['Relay_EARFCN'] = relay_radio_info['earfcn']
            result_dict['Relay_PCI'] = relay_radio_info['pci']
            # print result_dict
            #
            # utworzenie listy wartości sprawdzanych w teście udp, od 70% do 130% ze skokiem 10%
            theo_dl = readOption(key+'_theo_dl')
            theo_ul = readOption(key+'_theo_ul')
            # udp_dl_list = createBandwidthList(theo_dl, 70, 130, 5)
            # udp_ul_list = createBandwidthList(theo_ul, 70, 130, 5)
            udp_dl_list = createBandwidthList(theo_dl, 90, 130, 5)
            udp_ul_list = createBandwidthList(theo_ul, 90, 130, 5)
            parallel_list = [1, 2, 4, 8, 10, 16, 32]
            # parallel_list = [1, 2, 4, 6, 8, 10, 12, 16, 20, 32]

            # # #szybki pomiar
            # udp_dl_list = [100]
            # udp_ul_list = [10]
            # parallel_list = [8, 16]

            logging.info('List of dl udp bandwidth: %s' % (';'.join(map(str, udp_dl_list))))
            logging.info('List of ul udp bandwidth: %s' % (';'.join(map(str, udp_ul_list))))
            logging.info('List of tcp parallel nr threads: %s' % (';'.join(map(str, parallel_list))))

            # wlasciwe pomiary przeplywnosci relaya
            time_s = readOption('iperf_duration', True)
            add_iperf_parameters_udp = ' -l 1360 '
            add_iperf_parameters_tcp = ''
            port_nr = 5222
            # iperf_m = IperfManager(ubuntu_iperf_dict, au_iperf_dict)
            # # iperf_m = IperfManager(ubuntu_iperf_dict, ue_iperf_dict)
            # dl_tcp = iperf_m.performDlTcpTest(parallel_list, time_s, port_nr, add_iperf_parameters_tcp, add_iperf_parameters_udp)
            # ul_tcp = iperf_m.performUlTcpTest(parallel_list, time_s, port_nr, add_iperf_parameters_tcp, add_iperf_parameters_udp)
            # dl_udp = iperf_m.performDlUdpTest(udp_dl_list, time_s, port_nr, add_iperf_parameters_udp, add_iperf_parameters_udp)
            # ul_udp = iperf_m.performUlUdpTest(udp_ul_list, time_s, port_nr, add_iperf_parameters_udp, add_iperf_parameters_udp)
            # logging.info('Relay RESULTS:\nDL TCP: %f\n UL TCP: %f\n DL UDP: %f\n UL UDP: %f\n' % (dl_tcp, ul_tcp, dl_udp, ul_udp))
            # # wczytanie otrzymanych wartosci do slownika wynikowego
            # result_dict['Relay_DL_UDP'] = dl_udp
            # result_dict['Relay_UL_UDP'] = ul_udp
            # result_dict['Relay_DL_TCP'] = dl_tcp
            # result_dict['Relay_UL_TCP'] = ul_tcp

            # # #sprawdzenie czy UE jest online
            # while not pingHost(ue_iperf_dict['iperf_ip']):
            #     logging.error('UE is offline')
            #     time.sleep(5)
            # else:
            #     logging.info('UE is online, waiting %is to stable connection' % establishment_time)
            #     time.sleep(establishment_time)
            time.sleep(180)
            # # pobranie informacji radiowych z ue
            # kztech = KztechScraper(readOption('kztech_link_local'))
            # kztech.connnect()
            # ue_radio_info = kztech.getLteInfo()
            # print ue_radio_info
            # logging.info('UE radio info: %s' % ue_radio_info)
            # result_dict['UE_RSRP_0'] = ue_radio_info['rsrp_0']
            # result_dict['UE_RSRP_1'] = ue_radio_info['rsrp_1']
            # # result_dict['UE_RSSI'] = ue_radio_info['rssi']
            # result_dict['UE_RSRQ'] = ue_radio_info['rsrq']
            # result_dict['UE_SINR'] = ue_radio_info['sinr']
            # result_dict['UE_FREQ'] = ue_radio_info['dl_frequency']
            # result_dict['UE_PCI'] = ue_radio_info['pci']

            # pomiary przepływności dla UE
            iperf_m_ue = IperfManager(ubuntu_iperf_dict, ue_iperf_dict)
            dl_tcp = iperf_m_ue.performDlTcpTest(parallel_list, time_s, port_nr, add_iperf_parameters_tcp, add_iperf_parameters_tcp)
            ul_tcp = iperf_m_ue.performUlTcpTest(parallel_list, time_s, port_nr, add_iperf_parameters_tcp, add_iperf_parameters_tcp)
            dl_udp = iperf_m_ue.performDlUdpTest(udp_dl_list, time_s, port_nr, add_iperf_parameters_udp, add_iperf_parameters_udp)
            ul_udp = iperf_m_ue.performUlUdpTest(udp_ul_list, time_s, port_nr, add_iperf_parameters_udp, add_iperf_parameters_udp)
            logging.info('UE RESULTS:\nDL TCP: %f\n UL TCP: %f\n DL UDP: %f\n UL UDP: %f\n' % (dl_tcp, ul_tcp, dl_udp, ul_udp))
            # wczytanie otrzymanych wartosci do slownika wynikowego
            result_dict['UE_DL_UDP'] = dl_udp
            result_dict['UE_UL_UDP'] = ul_udp
            result_dict['UE_DL_TCP'] = dl_tcp
            result_dict['UE_UL_TCP'] = ul_tcp
            #
            # tu bedzie petla spr czy STATUS jest PASS or FAIL
            result_dict['STATUS'] = 'PASSED'
            #
            #wpisanie wynikow do pliku
            res_csv.writeDict(myHeaders, result_dict)

    amarisoft.disconnect()


if __name__ == '__main__':
    run()
