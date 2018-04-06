# -*- coding: utf-8 -*-

import logging
from ConfigParser import ConfigParser



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
