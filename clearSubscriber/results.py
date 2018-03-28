# -*- coding: utf-8 -*-
import csv

class Results(object):
    """"Klasa odpowiadajaca za zapis wynikow do pliku .csv"""
    def __init__(self, path):
        self.path = path
        # self.myFile

    def writeHeader(self, header_fields):
        myFile = open(self.path, 'wb')
        # jak mamy with to nie trzeba martwic sie o zamykanie pliku
        with myFile:
            writer = csv.DictWriter(myFile, fieldnames=header_fields)
            # zapisanie naglowkow do pliku
            writer.writeheader()

    def writeDict(self,header_fields, dict_fields):
        myFile = open(self.path, 'ab')
        # jak mamy with to nie trzeba martwic sie o zamykanie pliku
        with myFile:
            writer = csv.DictWriter(myFile, fieldnames=header_fields)
            # zapisanie naglowkow do pliku
            writer.writerow(dict_fields)
