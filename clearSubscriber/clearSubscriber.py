# -*- coding: utf-8 -*-

from ping import pingHost
from readINI import readOption, readSection
from ssh import ssh
import logging
import logger
import time
import timeout
import results



def run():
    # ustawinie loggera
    main_log_path = readOption('main_log_path')
    logger.setRootLogger(main_log_path)

    #wczytanie informacji o użytkowniku
    ue_dict, ue_list = readSection('subscriber_config')
    logging.info('Subscriber info : %s' % ue_dict)

    #wczytanie ip mme i spr czy jest osiagalne
    mme_ip = readOption('mme_ip')
    if pingHost(mme_ip):
        logging.info('Ping respond from MME: %s', mme_ip)
    else:
        logging.error('No response from MME: %s', mme_ip)
        exit(1)

    # połączenie do mme
    mme_connection = ssh(mme_ip, readOption('user'), readOption('password'))  # utworzenie obiektu ssh
    mme_connection.openShell()  # odpalanie indywidualnej powloki aby byla mozliwosc wprowadzania kilku komend nastepujacych po sobie
    mme_connection.readShell()  # wczytujemy pierwsze śmieci po podłączeniu się po ssh

    #wczytanie typu testu i spr czy apn/y są osiągalne po ip i w mme
    clear_type = readOption('type')
    logging.info('Test TYPE : %s' % clear_type)

    #weryfikacja ustawien poczatkowych w zalezności od typu testu
    verifyInitialStatus(mme_connection, clear_type, ue_dict)

    # Utworzenie pliku wynikowego
    res_csv = results.Results(readOption('result_path'))
    myHeaders = ['No', 'ClearType', 'ClearTime',
                 'AttachTime', 'ElapsedTime', 'STATUS']
    res_csv.writeHeader(myHeaders)
    #utworzenie slownika ktory bedzie przechowywal tymczasowe wyniki
    result_dict = dict((k, '') for k in myHeaders)
    result_dict['ClearType'] = clear_type

    no_time = 0
    # Wczytanie liczby petli
    loop_nr = int(readOption('repetitions_number'))
    logging.info('loop nr : %i'% loop_nr)

    # glowna petla
    for i in range(loop_nr):
        no_time += 1
        result_dict['No'] = no_time
        #usunięcie apna/calego uzytkownika
        if 'APN' in clear_type:
            apn_nr = clear_type[:4].lower()
            apn_ip = ue_dict[apn_nr + '_ip']
            clear_time = clearApn(mme_connection, ue_dict['imsi'], ue_dict[apn_nr])
            attach_time = waitForSingleApn(mme_connection, ue_dict['imsi'], ue_dict[apn_nr], ue_dict[apn_nr + '_ip'])
            elapsed_time = attach_time - clear_time
            result_dict['ClearTime'] = time.strftime("%H:%M:%S", time.gmtime(clear_time))
            result_dict['AttachTime'] = time.strftime("%H:%M:%S", time.gmtime(attach_time))
            result_dict['ElapsedTime'] = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
            result_dict['STATUS'] = 'PASSED'


        elif clear_type == 'ALL':
            clear_time = clearSubscriber(mme_connection, ue_dict['imsi'])

        else:
            logging.error('Unknown clear type')
        res_csv.writeDict(myHeaders, result_dict)


    mme_connection.closeConnection()

def waitForSingleApn(mme_ssh_obj, ue_imsi, apn_name, apn_ip):
    while True:
        if isSubscriberInMme(mme_ssh_obj, ue_imsi, apn_name) and pingHost(apn_ip):
            logging.info('APN %s reattached' % apn_name)
            a_time = time.time()
            return a_time
            break
        else:
            logging.info('Waiting for reattach and ping response...')
            time.sleep(1)


def waitForAllApn(mme_ssh_obj, ue_imsi, apn_name, apn_ip):
    while True:
        pass

def isSubscriberInMme(mme_ssh_obj, ue_imsi, apn_name):
    username = ue_imsi + '@' + apn_name
    mme_ssh_obj.sendShell("show subscribers username %s" % username)
    time.sleep(0.5)
    output = mme_ssh_obj.readShell()
    if 'Total subscribers matching' in output:
        logging.info('User %s is attached to MME' % username)
        return True
    else:
        logging.error('User %s not found in MME' % username)
        return False

def verifyInitialApnStatus(mme_ssh_obj, ue_imsi, apn_name, apn_ip):
    # apn_nr = clear_type[:4].lower()
    # apn_ip = ue_dict[apn_nr + '_ip']
    if pingHost(apn_ip):
        logging.info('Ping respond from APN %s : %s' % (apn_name, apn_ip))
    else:
        logging.error('No response from APN %s : %s' % (apn_name, apn_ip))
        exit(1)
    username = ue_imsi + '@' + apn_name
    mme_ssh_obj.sendShell("show subscribers username %s" % username)
    time.sleep(1)
    output = mme_ssh_obj.readShell()
    if 'Total subscribers matching' in output:
        logging.info('User %s is in correct MME' % username)
    else:
        logging.error('User %s not found in MME' % username)

def verifyInitialStatus(mme_ssh_obj, clear_type, ue_dict):
    if 'APN' in clear_type:
        apn_nr = clear_type[:4].lower()
        apn_ip = ue_dict[apn_nr+'_ip']
        verifyInitialApnStatus(mme_ssh_obj, ue_dict['imsi'], ue_dict[apn_nr], apn_ip)
    else:
        for key in ue_dict:
            if 'ip' in key:
                apn_ip = ue_dict[key]
                apn_nr = key[:4]
                verifyInitialApnStatus(mme_ssh_obj, ue_dict['imsi'], ue_dict[apn_nr], apn_ip)

def clearApn(mme_ssh_obj, ue_imsi, apn_name):
    username = ue_imsi + '@' + apn_name
    mme_ssh_obj.sendShell("clear subscribers username %s" % username)
    time.sleep(0.5)
    mme_ssh_obj.sendShell("yes")
    time.sleep(0.5)
    output = mme_ssh_obj.readShell()
    if 'Number of subscribers cleared' in output:
        logging.info('User %s has been cleared from MME properly' % username)
        c_time = time.time()
        return c_time
    else:
        logging.error('No subscribers match the specified criteria')

def clearSubscriber(mme_ssh_obj, ue_imsi):
    mme_ssh_obj.sendShell("clear subscribers imsi %s" % ue_imsi)
    time.sleep(0.5)
    mme_ssh_obj.sendShell("yes")
    time.sleep(0.5)
    output = mme_ssh_obj.readShell()
    if 'Number of subscribers cleared' in output:
        logging.info('Subscriber %s has been cleared from MME properly' % ue_imsi)
        c_time = time.time()
        return c_time
    else:
        logging.error('No subscribers match the specified criteria')



if __name__ == '__main__':
    run()