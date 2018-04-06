# -*- coding: utf-8 -*-

import logger
from iperfManager import IperfManager, createBandwidthList
from ping import pingHost
import logging
from nbi import Argstruct, nbi
import node
from nodeLogger import RelayLogger
import results
import threading
import multiprocessing
from kztechScraperRemote import KztechScraperRemote
import time
from readINI import readOption, readSection



def run():
    # ustawinie loggera
    main_log_path = readOption('main_log_path')
    logger.setRootLogger(main_log_path)

    # utworzenie obiektu informacji o wykonywanym teście
    test_config_info = results.TestConfigInfo(readOption('test_info_path'))
    test_config_info.writeTestName('e2e Throughput')
    test_config_info.writeStartTime()

    # odczytanie parametrów netspana dla eNBs
    enb_netspan_dict, enb_netspan_list = readSection('enbs_netspan_config')

    # sprawdzenie czy Netspan jest dostępny
    if pingHost(enb_netspan_dict['netspan_ip']):
        logging.info('Ping respond from enbs Netspan: %s', enb_netspan_dict['netspan_ip'])
    else:
        logging.error('No response from enbs Netspan: %s', enb_netspan_dict['netspan_ip'])
        exit(1)
    # utowrzenie obiektu do połączenia z netspanem i weryfikacja wersji Netspana
    netspan_enb = nbi(enb_netspan_dict['netspan_ip'],
                  enb_netspan_dict['netspan_sr'],
                  enb_netspan_dict['netspan_user'],
                  enb_netspan_dict['netspan_pass'])
    logging.info('eNBs Netspan version: %s', netspan_enb.getNmsVersion())

    # # utworzenie obiektu enb B25, wczytanie informacji o nr celli oraz wyłączenie nadawania
    try:
        enb_b25 = node.Node(readOption('enb_name_band25'))
        enb_b25_profiles = [readOption('enb_band25_profile1'), readOption('enb_band25_profile2')]
        enb_config = enb_b25.enbConfigGet(netspan_enb)
        enb_b25_cell_number = ''.join(enb_config['CellNumber'])
        logging.info('Cell number for enb band 41: %s', enb_b25_cell_number)
        enb_b25.enbStateSet(netspan_enb, 'OutOfService')
    except:
        logging.error('Could not read info about enb band 25')

    # # utworzenie obiektu enb B41
    try:
        enb_b41 = node.Node(readOption('enb_name_band41'))
        enb_b41_profiles = [readOption('enb_band41_profile1'),readOption('enb_band41_profile2')]
        enb_config = enb_b41.enbConfigGet(netspan_enb)
        enb_b41_cell_number = ''.join(enb_config['CellNumber'])
        logging.info('Cell number for enb band 41: %s', enb_b41_cell_number)
        enb_b41.enbStateSet(netspan_enb, 'OutOfService')
    except:
        logging.error('Could not read info about enb band 41')

    # odczytanie parametrów netspana dla AU
    netspan_dict, netspan_list = readSection('netspan_config')

    # sprawdzenie czy Netspan jest dostępny
    if pingHost(netspan_dict['netspan_ip']):
        logging.info('Ping respond from au Netspan: %s', netspan_dict['netspan_ip'])
    else:
        logging.error('No response from au Netspan: %s', netspan_dict['netspan_ip'])
        exit(1)
    # utowrzenie obiektu do połączenia z netspanem i weryfikacja wersji Netspana
    netspan = nbi(netspan_dict['netspan_ip'],
                      netspan_dict['netspan_sr'],
                      netspan_dict['netspan_user'],
                      netspan_dict['netspan_pass'])
    logging.info('eNBs Netspan version: %s', netspan_enb.getNmsVersion())

    # wczytanie informacji o wezlach iperfowych
    ubuntu_iperf_dict, ubuntu_iperf_list = readSection('iperf_ubuntu_config')
    au_iperf_dict, au_iperf_list = readSection('au_config')
    ue_iperf_dict, ue_iperf_list = readSection('ue_config')

    # utworzenie obiektu AU
    au = node.Node(readOption('node_name'))

    # pobranie i zapis informacji o urzadzeniu
    test_config_info.writeNodeInfo(netspan, readOption('node_name'))

    # Utworzenie pliku wynikowego
    res_csv = results.Results(readOption('result_path'))
    myHeaders = ['Profile_Name', 'Relay_RSRP', 'Relay_RSSI',
                 'Relay_RSRQ', 'Relay_SINR', 'Relay_EARFCN',
                 'Relay_PCI', 'Relay_DL_UDP', 'Relay_UL_UDP', 'Relay_DL_TCP', 'Relay_UL_TCP', 'Relay_DL+UL_UDP',
                 'UE_RSRP_0', 'UE_RSRP_1', 'UE_RSRQ', 'UE_SINR',
                 'UE_FREQ', 'UE_PCI', 'UE_DL_UDP', 'UE_UL_UDP', 'UE_DL_TCP', 'UE_UL_TCP', 'UE_DL+UL_UDP', 'STATUS']

    res_csv.writeHeader(myHeaders)
    # utworzenie slownika ktory bedzie przechowywal tymczasowe wyniki
    result_dict = dict((k, '') for k in myHeaders)

    # czas na stabilizacje połączenia
    establishment_time = readOption('establishment_time', True)

    try:
        if enb_b41:
            logging.info('eNB band 41 in use')
    except:
        logging.error('eNB band 41 not defined!!!')

    for profile in enb_b41_profiles:
        result_dict['Profile_Name'] = profile
        #zmiana statusu na InService
        enb_b41.enbStateSet(netspan_enb, 'InService')
        logging.info('Change eNB to InService state')
        #załadowanie odpowiedniego profilu radiowego
        enb_b41.enbConfigSet(netspan_enb, profile, enb_b41_cell_number)
        logging.info('Set radio profile: %s to eNB: %s'%(profile, enb_b41.node_name))
        time.sleep(15)
        #reprovision node'a
        enb_b41.nodeReprovision(netspan_enb)
        logging.info('Reprovision of eNB: %s'%enb_b41.node_name)
        time.sleep(15)
        #forced reset node'a
        enb_b41.nodeResetForced(netspan_enb)
        logging.info('Forced Reset of eNB: %s' % enb_b41.node_name)
        time.sleep(60)

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

        # utworzenie listy wartości sprawdzanych w teście udp, od 70% do 130% ze skokiem 10%
        theo_dl = readOption(profile+'_theo_dl')
        theo_ul = readOption(profile+'_theo_ul')
        udp_dl_list = createBandwidthList(theo_dl, 70, 130, 5)
        udp_ul_list = createBandwidthList(theo_ul, 70, 130, 5)
        # udp_dl_list = createBandwidthList(theo_dl, 90, 130, 5)
        # udp_ul_list = createBandwidthList(theo_ul, 90, 130, 5)
        parallel_list = [1, 2, 4, 8, 10, 16, 32]
        # parallel_list = [1, 2, 4, 6, 8, 10, 12, 16, 20, 32]

        # #szybki pomiar
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
        iperf_m = IperfManager(ubuntu_iperf_dict, au_iperf_dict)
        # iperf_m = IperfManager(ubuntu_iperf_dict, ue_iperf_dict)
        dl_tcp = iperf_m.performDlTcpTest(parallel_list, time_s, port_nr, add_iperf_parameters_tcp, add_iperf_parameters_tcp)
        ul_tcp = iperf_m.performUlTcpTest(parallel_list, time_s, port_nr, add_iperf_parameters_tcp, add_iperf_parameters_tcp)
        dl_udp = iperf_m.performDlUdpTest(udp_dl_list, time_s, port_nr, add_iperf_parameters_tcp, add_iperf_parameters_tcp)
        ul_udp = iperf_m.performUlUdpTest(udp_ul_list, time_s, port_nr, add_iperf_parameters_tcp, add_iperf_parameters_tcp)
        logging.info('Relay RESULTS:\nDL TCP: %f\n UL TCP: %f\n DL UDP: %f\n UL UDP: %f\n' % (dl_tcp, ul_tcp, dl_udp, ul_udp))
        # wczytanie otrzymanych wartosci do slownika wynikowego
        result_dict['Relay_DL_UDP'] = dl_udp
        result_dict['Relay_UL_UDP'] = ul_udp
        result_dict['Relay_DL_TCP'] = dl_tcp
        result_dict['Relay_UL_TCP'] = ul_tcp
        results_dl_l = []
        results_ul_l = []
        #UDP UL i DL jednocześnie
        for x, y in zip(udp_dl_list, udp_ul_list):
            logging.info('DL bandwidth: %f, UL bandwidth: %f' % (x, y))
            thread1 = threading.Thread(target=iperf_m.performSimDlUdpTest, args=(
                results_dl_l,[x], time_s, port_nr, add_iperf_parameters_tcp, add_iperf_parameters_tcp)).start()
            thread2 = threading.Thread(target=iperf_m.performSimUlUdpTest, args=(
                results_ul_l, [y], time_s, port_nr + 1, add_iperf_parameters_tcp, add_iperf_parameters_tcp)).start()
            time.sleep(time_s + 20)
            logging.info(results_dl_l)
            logging.info(results_ul_l)

        results_sum = [x + y for x, y in zip(results_dl_l, results_ul_l)]
        logging.info('List of summed values: %s' % results_sum)
        max_index = results_sum.index(max(results_sum))
        logging.info('The highest index: %i ' % max_index)
        result_dict['Relay_DL+UL_UDP'] = (str(results_dl_l[max_index]) + '+' + str(results_ul_l[max_index]))


        # # #sprawdzenie czy UE jest online
        # while not pingHost(ue_iperf_dict['iperf_ip']):
        #     logging.error('UE is offline')
        #     time.sleep(5)
        # else:
        #     logging.info('UE is online, waiting %is to stable connection' % establishment_time)
        #     time.sleep(establishment_time)
        time.sleep(180)
        # pobranie informacji radiowych z ue
        path = '/home/airspan/kztechScraper_local.py'
        kztech = KztechScraperRemote(ue_iperf_dict, path)
        kztech.connnect()
        ue_radio_info = kztech.getLteInfo()
        logging.info(ue_radio_info)
        logging.info('UE radio info: %s' % ue_radio_info)
        result_dict['UE_RSRP_0'] = ue_radio_info['rsrp_0']
        result_dict['UE_RSRP_1'] = ue_radio_info['rsrp_1']
        # result_dict['UE_RSSI'] = ue_radio_info['rssi']
        result_dict['UE_RSRQ'] = ue_radio_info['rsrq']
        result_dict['UE_SINR'] = ue_radio_info['sinr']
        result_dict['UE_FREQ'] = ue_radio_info['dl_frequency']
        result_dict['UE_PCI'] = ue_radio_info['pci']

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


        #jednoczesny UL i DL dla UE
        results_dl_l = []
        results_ul_l = []
        #UDP UL i DL jednocześnie
        for x, y in zip(udp_dl_list, udp_ul_list):
            logging.info('DL bandwidth: %f, UL bandwidth: %f' % (x, y))
            thread1 = threading.Thread(target=iperf_m_ue.performSimDlUdpTest, args=(
                results_dl_l,[x], time_s, port_nr, add_iperf_parameters_udp, add_iperf_parameters_udp)).start()
            thread2 = threading.Thread(target=iperf_m_ue.performSimUlUdpTest, args=(
                results_ul_l, [y], time_s, port_nr + 1, add_iperf_parameters_udp, add_iperf_parameters_udp)).start()
            time.sleep(time_s + 20)
            logging.info(results_dl_l)
            logging.info(results_ul_l)

        results_sum = [x + y for x, y in zip(results_dl_l, results_ul_l)]
        logging.info('List of summed values: %s' % results_sum)
        max_index = results_sum.index(max(results_sum))
        logging.info('The highest index: %i ' % max_index)
        result_dict['UE_DL+UL_UDP'] = (str(results_dl_l[max_index]) + '+' + str(results_ul_l[max_index]))


        # tu bedzie petla spr czy STATUS jest PASS or FAIL
        result_dict['STATUS'] = 'PASSED'
        #
        #wpisanie wynikow do pliku
        res_csv.writeDict(myHeaders, result_dict)

    # try:
    #     if enb_b25:
    #         logging.info('eNB band 25 in use')
    # except:
    #     logging.error('eNB band 25 not defined!!!')



if __name__ == '__main__':
    run()
