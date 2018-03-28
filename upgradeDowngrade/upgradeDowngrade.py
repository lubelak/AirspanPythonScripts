# -*- coding: utf-8 -*-


#AU image upgrade script. Author: Krystian Lubelski

import time ,datetime, re , random, sys, os
import os
import logging
import logger
import node
import platform
from nbi import Argstruct, nbi
from ConfigParser import ConfigParser
import timeout
import results


def readOption(req_opt,is_int = False, path='config.ini'):
    """" Funkcja zwracajaca wartość z pliku ini.
        Zwraca słownik.
    """
    config = ConfigParser()
    config.read(path)
    output = {}
    for section in config.sections():
        for option in config.options(section):
            if (option == req_opt and  not is_int) :
                output = config.get(section, option)
            elif (option == req_opt and is_int):
                output = config.getint(section, option)
    if output:
        return output
    else:
        logging.error('No such option/section like %s in %s file' % (req_opt, path))
        exit(1)
def readSection(req_sec, path='config.ini'):
    """" Funkcja zwracajaca wartość z pliku ini.
        Zwraca słownik i liste.
    """
    config = ConfigParser()
    config.read(path)
    output_dic = {}
    output_list = []
    for section in config.sections():
        for option in config.options(section):
            if section == req_sec:
                output_dic[option] = config.get(section, option)
                output_list.append({option : config.get(section, option)})
    if output_list:
        return output_dic, output_list
    else:
        logging.error('No such section like %s in %s file' % (req_sec, path))
        exit(1)

def run():
    #ustawinie loggera
    main_log_path = readOption('main_log_path')
    logger.setRootLogger(main_log_path)

    #odczytanie adresu netspana
    netspan_ip = readOption('netspan_ip')

    #sprawdzenie czy Netspan jest dostępny
    if pingHost(netspan_ip):
        logging.info('Ping respond from Netspan: %s', netspan_ip)
    else:
        logging.error('No response from Netspan: %s', netspan_ip)
        exit(1)
    #utowrzenie obiektu do połączenia z netspanem i weryfikacja wersji Netspana
    netspan = nbi(netspan_ip,
                  readOption('netspan_sr'),
                  readOption('netspan_user'),
                  readOption('netspan_pass'))
    logging.info('Netspan version: %s', netspan.getNmsVersion())

    #utworzenie obiektu AU
    au = node.Node(readOption('node_name'))
    # #sprawdzenie czy jest online
    if not au.isOnline(netspan):
        exit(1)
    #update parametrów z netspana
    au.updateNodeInfo(netspan)
    au.updateNodeSoftwareStatus(netspan)
    logging.info('Node info: %s' % au.node_info)
    logging.info('Node software status: %s' % au.node_software_status)

    #wczytanie commercial images
    commercial_images_dict , commercial_images_list = readSection('from_images_config')

    #wczytanie tested image
    tested_image = readOption('img')

    #sprawdzenie sw
    verifyImages(netspan, commercial_images_dict , au.node_info)

    #Utworzenie pliku wynikowego
    res_csv = results.Results(readOption('result_path'))
    # print type(au.node_info['HardwareType'])
    # print au.node_info['HardwareType'][0]
    if au.node_info['HardwareCategory'][0] == 'AirUnity':
        myHeaders = ['No','From_iRelay_SW','From_eNB_SW',
                    'To_SW_name','To_iRelay_SW','To_eNB_SW',
                    'Start_Time','Finish_Time','Elapsed_Time','TYPE','STATUS']
    elif au.node_info['HardwareType'][0] == 'iBridge 460' or au.node_info['HardwareType'][0] == 'iRelay 464':
        myHeaders = ['No', 'From_SW','To_SW_name', 'To_SW',
                     'Start_Time', 'Finish_Time', 'Elapsed_Time', 'TYPE', 'STATUS']
    else:
        logging.error('Unknown HardwareType')
        exit(1)


    res_csv.writeHeader(myHeaders)
    #utworzenie slownika ktory bedzie przechowywal tymczasowe wyniki
    result_dict = dict((k, '') for k in myHeaders)

    no_time = 0
    # Wczytanie liczby petli
    loop_nr = int(readOption('repetitions_number'))
    logging.info('loop nr : %i'% loop_nr)

    #petla instalujaca odpowiedni sw
    for i in range(loop_nr):
        for img in commercial_images_list:
            for key in img:
                for x in range(3):
                    no_time += 1
                    result_dict['No'] = no_time
                    if (no_time%3) == 1:
                        result_dict = upgradeProcedure(au,netspan,img[key],result_dict,res_csv,myHeaders, 'SET PROPER SW')
                    elif (no_time%3) == 2:
                        result_dict = upgradeProcedure(au, netspan, tested_image, result_dict, res_csv, myHeaders,
                                                       'UPGRADE')
                    elif (no_time%3) == 0:
                        result_dict = upgradeProcedure(au, netspan, img[key], result_dict, res_csv, myHeaders,
                                                       'DOWNGRADE')
                    res_csv.writeDict(myHeaders, result_dict)

def upgradeProcedure (node_obj, nbi_obj, img_name, dic_res, res_obj,headrs, type_name):
    node_obj.updateNodeSoftwareStatus(nbi_obj)
    # result_dict['From_SW_name'] = au.node_software_status['']
    while not node_obj.node_software_status['RunningVersion']:
        node_obj.updateNodeSoftwareStatus(nbi_obj)
        logging.warning('Can not read Running Version from Node. Waiting 5s and try again')
        time.sleep(5)
    if node_obj.node_info['HardwareCategory'][0] == 'AirUnity':
        dic_res['From_iRelay_SW'] = node_obj.node_software_status['RunningVersion'][0]
        dic_res['From_eNB_SW'] = node_obj.node_software_status['RunningVersion'][1]
    elif node_obj.node_info['HardwareType'][0] == 'iBridge 460' or node_obj.node_info['HardwareType'][0] == 'iRelay 464':
        dic_res['From_SW'] = node_obj.node_software_status['RunningVersion']
    else:
        logging.error('Unknown HardwareType')
        exit(1)
    # instalacja sw
    node_obj.installSoftware(nbi_obj, img_name)
    start_time = time.time()
    dic_res['Start_Time'] = time.strftime("%H:%M:%S", time.gmtime(start_time))
    logging.info('Waiting 30s....')
    time.sleep(30)
    # uruchomienie czekania na upgrade nie dłuzej niz okreslona liczbe sekund
    func = timeout.timeout(timeout=(readOption('timeout_min', True)*60))(node_obj.waitForIdleState)
    try:
        func(nbi_obj)
    except ValueError as err:
        logging.error(err)
        dic_res['STATUS'] = 'FAILED'
        res_obj.writeDict(headrs, dic_res)
        exit(1)
    finish_time = time.time()
    elapsed_time = finish_time - start_time
    dic_res['Finish_Time'] = time.strftime("%H:%M:%S", time.gmtime(finish_time))
    dic_res['Elapsed_Time'] = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
    node_obj.updateNodeSoftwareStatus(nbi_obj)
    dic_res['To_SW_name'] = img_name
    dic_res['STATUS'] = 'PASSED'
    dic_res['TYPE'] = type_name
    while not node_obj.node_software_status['RunningVersion']:
        node_obj.updateNodeSoftwareStatus(nbi_obj)
        time.sleep(5)
    if node_obj.node_info['HardwareCategory'][0] == 'AirUnity':
        dic_res['To_iRelay_SW'] = node_obj.node_software_status['RunningVersion'][0]
        dic_res['To_eNB_SW'] = node_obj.node_software_status['RunningVersion'][1]
    elif node_obj.node_info['HardwareType'][0] == 'iBridge 460' or node_obj.node_info['HardwareType'][0] == 'iRelay 464':
        dic_res['To_SW'] = node_obj.node_software_status['RunningVersion']
    else:
        logging.error('Unknown HardwareType')

    return dic_res
    # try:
    #     result_dict['To_iRelay_SW'] = au.node_software_status['RunningVersion'][0]
    #     result_dict['To_eNB_SW'] = au.node_software_status['RunningVersion'][1]
    # except:
    #     logging.warning('Can not read Running Version from Node')
    #     result_dict['To_iRelay_SW'] = ''
    #     result_dict['To_eNB_SW'] = ''

def verifyImages(nbi_obj, images_dic, node_info):
    for key in images_dic:
        args = Argstruct({'values': ['Name=' + images_dic[key]], 'delempty': True})
        #sprawdzenie gdzie znajduje się odpowiedni obiekt
        xml = nbi_obj.action('Software', 'SoftwareImageGet', args)
        # doc = nbi_obj.formatXmlResponse(xml)
        #pobranie odpowiednich informacji o obiekcie
        image_record = nbi_obj.getFieldList(xml, ['Name', 'HardwareCategory', 'Version', 'ImageType'])
        if image_record['Version']:
            logging.info('SW %s exist, details below: ', key)
            logging.info(image_record)
            if node_info['HardwareCategory']==image_record['HardwareCategory']:
                logging.info('Node HardwareCategory: %s match to SW %s HardwareCategory: %s',node_info['HardwareCategory'],key,image_record['HardwareCategory'])
            else:
                logging.error('Node HardwareCategory: %s does not match to SW %s HardwareCategory: %s',node_info['HardwareCategory'],key,image_record['HardwareCategory'])
                exit(1)
        else:
            logging.error('SW %s does not exist in Netspan. Please check name or Netspan settings',key )
            exit(1)

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
        logging.info("Unknown operating system")
        # ping1 = "ping -c 1 "

    comm = ping1 + ip  # utworzenie komendy jaka ma być wykonana w systemie
    logging.info("Ping command: %s"%comm)
    response = os.popen(comm)  # otwarcie pipe z komendą do pingowania wybranego adresu
    for line in response.readlines():  # wczytanie całej odpowiedzi (do EOF) jako listy poszczególnych linii
        if (line.count("TTL") or line.count(
                "ttl")):  # sprawdzenie czy poszczególne linie zawierają słówko TTL (dla Windowsa) i ttl (dla Linuxa), jeśli tak oznacz to że jest odpowiedź od hosta.
            # logging.info(line.strip())  # Metoda Count() zwraca ile razy słowo występuje w liście
            # print ip, "--> Live"
            response.close()
            return True
            break
        # logging.info("No response from host: %s"%ip)
    return False


if __name__ == '__main__':
    run()