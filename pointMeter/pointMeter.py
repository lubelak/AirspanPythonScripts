# -*- coding: utf-8 -*-

import logger
import iperfManager
from ping import pingHost
import logging
import results
import sys
from gps import GpsManager
import argparse
from snmp import SnmpManager
import threading
import time
from readINI import readOption, readSection



def run():
    # ustawinie loggera
    main_log_path = readOption('main_log_path')
    logger.setRootLogger(main_log_path)

    #parser argumentow
    parser = argparse.ArgumentParser(description='This is the PointMeter script')
    parser.add_argument('-n', action='store_true', default=False, dest='new_file',
                        help='Create new results file. Warning: if file exist it will delete previous content!!!')
    parser.add_argument('-a', action='store_true', default=False, dest='app_file',
                        help='Append to existed result file')
    parser.add_argument('-p', action='store', dest='point_name',
                        help='Point name')
    parser_results = parser.parse_args()



    # Utworzenie pliku wynikowego
    res_csv = results.Results(readOption('result_path'))
    myHeaders = ['Test Loc.', 'GPS Lat', 'GPS Long',
                 'GPS Time GMT', 'RSRP0', 'RSRP1',
                 'RSRQ', 'UDP DL', 'UDP UL', 'TCP DL', 'TCP UL']

    # res_csv.writeHeader(myHeaders)
    # utworzenie slownika ktory bedzie przechowywal tymczasowe wyniki
    result_dict = dict((k, '') for k in myHeaders)

    # czy dopisywanie czy nowy plik
    if parser_results.app_file:
        logging.info('Results will be added to existed file')
    elif parser_results.new_file:
        res_csv.writeHeader(myHeaders)
        logging.info('New result file has been created')
    else:
        logging.error('User have to define how results will be handle\n -a append to existed file \n -n  new file')
        exit(1)

    if parser_results.point_name:
        logging.info('Point name: %s' % parser_results.point_name)
        result_dict['Test Loc.'] = parser_results.point_name

    else:
        logging.error('User have to define point name. Check help.')
        exit(1)

    #obsługa GPS
    gps = GpsManager()
    gps.connect('COM12')
    coor = gps.getCoordinates()
    gps.disconnect()
    result_dict['GPS Lat'] = coor['latitude']
    result_dict['GPS Long'] = coor['longitude']
    result_dict['GPS Time GMT'] = coor['timestamp']

    # sprawdzenie czy server snmp jest dostepny
    snmp_server_ip = readOption('snmp_host')
    if pingHost(snmp_server_ip):
        logging.info('Ping respond from snmp server: %s', snmp_server_ip)
    else:
        logging.error('No response from iperf server: %s', snmp_server_ip)
        exit(1)
    #obsługa snmp
    snmp_m = SnmpManager(readOption('snmp_host'))
    radio_info = snmp_m.getNetInfo()
    result_dict['RSRP0'] = radio_info['RSRP0']
    result_dict['RSRP1'] = radio_info['RSRP1']
    result_dict['RSRQ'] = radio_info['RSRQ']

    # sprawdzenie czy server iperfowy jest dostepny
    iperf_server_dict, iperf_server_list = readSection('iperf_server_config')

    if pingHost(iperf_server_dict['iperf_ip']):
        logging.info('Ping respond from iperf server: %s', iperf_server_dict['iperf_ip'])
    else:
        logging.error('No response from iperf server: %s', iperf_server_dict['iperf_ip'])
        res_csv.writeDict(myHeaders, result_dict)
        exit(1)

    # wlasciwe pomiary przeplywnosci
    time_s = readOption('iperf_duration', True)
    try:
        add_iperf_parameters_udp = readOption('udp_additional_parameters') + ' -u '
    except ValueError as err:
        add_iperf_parameters_udp = ' -u '
    try:
        add_iperf_parameters_tcp = readOption('tcp_additional_parameters')
    except ValueError as err:
        add_iperf_parameters_tcp = ''

    port_nr = readOption('port_nr', True)
    ue_ip = readOption('ue_ip')
    parallel = readOption('tcp_parallel', True)
    bandwidth_dl = readOption('udp_bandwidth_dl', True)
    bandwidth_ul = readOption('udp_bandwidth_ul', True)
    iperf_m = iperfManager.IperfManager(iperf_server_dict, ue_ip)
    try:
        dl_udp = iperf_m.performSingleDlUdpTest(bandwidth_dl, time_s, port_nr, add_iperf_parameters_udp,
                                                add_iperf_parameters_udp)
        logging.info('DL_UDP: %s' % dl_udp)
    except:
        dl_udp = 'Fail'
        logging.error('DL UDP Fail. Check LTE connection or iperf server.')
    try:
        ul_udp = iperf_m.performSingleUlUdpTest(bandwidth_ul, time_s, port_nr, add_iperf_parameters_udp,
                                                add_iperf_parameters_udp)
        logging.info('UL_UDP: %s' % ul_udp)
    except:
        ul_udp = 'Fail'
        logging.error('UL UDP Fail. Check LTE connection or iperf server.')
    try:
        dl_tcp = iperf_m.performSingleDlTcpTest(parallel,  time_s, port_nr, add_iperf_parameters_tcp,
                                                add_iperf_parameters_tcp)
        logging.info('DL_TCP: %s' % dl_tcp)
    except:
        dl_tcp = 'Fail'
        logging.error('DL TCP Fail. Check LTE connection or iperf server.')
    try:
        ul_tcp = iperf_m.performSingleUlTcpTest(parallel, time_s, port_nr, add_iperf_parameters_tcp,
                                                add_iperf_parameters_tcp)
        logging.info('UL_TCP: %s' % ul_tcp)
    except:
        ul_tcp = 'Fail'
        logging.error('UL TCP Fail. Check LTE connection or iperf server.')

    logging.info('Summarized results: DL_UDP: %s UL_UDP: %s DL_TCP: %s UL_TCP: %s' % (dl_udp, ul_udp, dl_tcp, ul_tcp))

    result_dict['UDP DL'] = dl_udp
    result_dict['UDP UL'] = ul_udp
    result_dict['TCP DL'] = dl_tcp
    result_dict['TCP UL'] = ul_tcp

    # wpisanie wynikow do pliku
    res_csv.writeDict(myHeaders, result_dict)


if __name__ == '__main__':
    run()