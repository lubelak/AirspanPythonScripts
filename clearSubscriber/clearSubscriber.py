# -*- coding: utf-8 -*-

from ping import pingHost
from readINI import readOption, readSection
from ssh import ssh
import logging
import logger
import time
import timeout
import results
import random
import collections



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

    no_time = 0
    # Wczytanie liczby petli
    loop_nr = int(readOption('repetitions_number'))
    logging.info('loop nr : %i'% loop_nr)

    # glowna petla
    if clear_type == 'all':
        ordered_apn_dict, ordered_ip_dict = userDictParser(ue_dict)
        for k in ordered_apn_dict:
            for i in range(loop_nr):
                no_time += 1
                result_dict['No'] = no_time
                result_dict = clearAndWaitToAttach(mme_connection, ue_dict, result_dict, k)
                # #wpisanie wynikow do pliku
                res_csv.writeDict(myHeaders, result_dict)
                sleepRandomMins(5)
        for i in range(loop_nr):
            no_time += 1
            result_dict['No'] = no_time
            result_dict = clearAndWaitToAttach(mme_connection, ue_dict, result_dict, 'subscriber')
            # #wpisanie wynikow do pliku
            res_csv.writeDict(myHeaders, result_dict)
            sleepRandomMins(5)
    else:
        for i in range(loop_nr):
            no_time += 1
            result_dict['No'] = no_time
            result_dict = clearAndWaitToAttach(mme_connection, ue_dict, result_dict, clear_type)
            # #wpisanie wynikow do pliku
            res_csv.writeDict(myHeaders, result_dict)
            # #odczekanie randomowego czasu
            sleepRandomMins(5)

    mme_connection.closeConnection()

def sleepRandomMins(mins):
    #odczekanie randomowego czasu
    sleep_time = random.randint(1, mins)
    logging.info('sleeping %i minutes...' % sleep_time)
    time.sleep(sleep_time*60)


# def waitForSingleApn(mme_ssh_obj, ue_imsi, apn_name, apn_ip):
#     while True:
#         if isSubscriberInMme(mme_ssh_obj, ue_imsi, apn_name) and pingHost(apn_ip):
#             logging.info('APN %s reattached' % apn_name)
#             # a_time = time.time()
#             # return a_time
#             break
#         else:
#             logging.info('Waiting for reattach and ping response...')
#             time.sleep(1)
def clearAndWaitToAttach(mme_ssh_obj, user_dict, result_dict, clear_type):
    result_dict['ClearType'] = clear_type
    if 'apn' in clear_type:
        apn_nr = clear_type[:4].lower()
        apn_ip = user_dict[apn_nr + '_ip']
        clear_time = clearApn(mme_ssh_obj, user_dict['username'], user_dict[apn_nr])
    elif clear_type == 'subscriber':
        clear_time = clearSubscriber(mme_ssh_obj, user_dict['imsi'])
        waitForAllApn(mme_ssh_obj, user_dict)

    else:
        logging.error('Unknown clear type')
        exit(1)

    #oczekiwanie nie dluzej niz timeout
    func = timeout.timeout(timeout=(readOption('timeout_min', True) * 60))(waitForAllApn)
    try:
        attach_time = func(mme_ssh_obj, user_dict)
    except ValueError as err:
        logging.error(err)
        result_dict['STATUS'] = 'FAILED'
        return result_dict

    elapsed_time = attach_time - clear_time
    result_dict['ClearTime'] = time.strftime("%H:%M:%S", time.gmtime(clear_time))
    result_dict['AttachTime'] = time.strftime("%H:%M:%S", time.gmtime(attach_time))
    result_dict['ElapsedTime'] = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
    result_dict['STATUS'] = 'PASSED'
    return result_dict

def userDictParser(user_dict):
    # parsowanie słownika info o użytkowniku
    ip_dict = {}
    apn_dict = {}
    for key in user_dict:
        if 'ip' in key:
            ip_dict[key] = user_dict[key]
        elif 'apn' in key:
            apn_dict[key] = user_dict[key]
            # postortowanie słownika od apn1 do apn3
    ordered_ip_dict = collections.OrderedDict(sorted(ip_dict.items()))
    ordered_apn_dict = collections.OrderedDict(sorted(apn_dict.items()))
    return ordered_apn_dict, ordered_ip_dict

def waitForAllApn(mme_ssh_obj, user_dict):
    ue_username = user_dict['username']
    ordered_apn_dict, ordered_ip_dict = userDictParser(user_dict)
    # liczba zdefiniowanych apnów w pliku ini
    apn_amount = len(ordered_apn_dict)
    logging.info('Nr of defined APNs: %i' % apn_amount)
    success_count = 0
    while success_count < apn_amount :
        success_count = 0
        for k in ordered_apn_dict:
            apn_name = ordered_apn_dict[k]
            apn_ip = ordered_ip_dict[k + '_ip']
            if  verifyApnStatus(mme_ssh_obj, ue_username, apn_name, apn_ip):
                success_count += 1
        logging.info('Success count: %i' % success_count)
    else:
        a_time = time.time()
        return a_time

def isSubscriberInMme(mme_ssh_obj, ue_username, apn_name):
    username = ue_username + '@' + apn_name
    mme_ssh_obj.sendShell("show subscribers username %s" % username)
    time.sleep(0.5)
    output = mme_ssh_obj.readShell()
    if 'Total subscribers matching' in output:
        logging.info('User %s is attached to MME' % username)
        return True
    else:
        logging.error('User %s not found in MME' % username)
        return False

def verifyApnStatus(mme_ssh_obj, ue_username, apn_name, apn_ip):
    if isSubscriberInMme(mme_ssh_obj, ue_username, apn_name) and pingHost(apn_ip):
        logging.info('APN %s reattached' % apn_name)
        return True
    else:
        logging.info('APN %s not reattach' % apn_name)
        return False

def verifyInitialApnStatus(mme_ssh_obj, ue_username, apn_name, apn_ip):
    # apn_nr = clear_type[:4].lower()
    # apn_ip = ue_dict[apn_nr + '_ip']
    if pingHost(apn_ip):
        logging.info('Ping respond from APN %s : %s' % (apn_name, apn_ip))
    else:
        logging.error('No response from APN %s : %s' % (apn_name, apn_ip))
        exit(1)
    username = ue_username + '@' + apn_name
    mme_ssh_obj.sendShell("show subscribers username %s" % username)
    time.sleep(1)
    output = mme_ssh_obj.readShell()
    if 'Total subscribers matching' in output:
        logging.info('User %s is in correct MME' % username)
    else:
        logging.error('User %s not found in MME' % username)

def verifyInitialStatus(mme_ssh_obj, clear_type, ue_dict):
    if 'apn' in clear_type:
        apn_nr = clear_type[:4].lower()
        apn_ip = ue_dict[apn_nr+'_ip']
        verifyInitialApnStatus(mme_ssh_obj, ue_dict['username'], ue_dict[apn_nr], apn_ip)
    else:
        for key in ue_dict:
            if 'ip' in key:
                apn_ip = ue_dict[key]
                apn_nr = key[:4]
                verifyInitialApnStatus(mme_ssh_obj, ue_dict['username'], ue_dict[apn_nr], apn_ip)

def clearApn(mme_ssh_obj, ue_username, apn_name):
    username = ue_username + '@' + apn_name
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