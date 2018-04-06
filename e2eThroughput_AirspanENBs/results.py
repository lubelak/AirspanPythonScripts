# -*- coding: utf-8 -*-
import csv
import node
from nbi import  Argstruct, nbi
import time


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

class TestConfigInfo(object):
    """Klasa która odpowiada za wygenerowanie pliku z informacjami o danym teście"""
    def __init__(self, path):
        self.path = path
        myFile = open(self.path, 'wb')
        myFile.close()

    def writeList(self, list_obj):
        myFile = open(self.path, 'ab')
        # jak mamy with to nie trzeba martwic sie o zamykanie pliku
        with myFile:
            for dict in list_obj:
                # print type(dict)
                myFile.write(''.join('{},{}\n'.format(key, val) for key, val in dict.items()))
            # writer = csv.DictWriter(myFile, fieldnames=header_fields)
            # zapisanie naglowkow do pliku
            # writer.writerow(dict_fields)
    def writeTestName(self, test_name):
        tmp_list = [{'TestName': test_name}]
        self.writeList(tmp_list)

    def writeStartTime(self):
        tmp_list = [{'StartTime': time.strftime("%d %b %Y %H:%M:%S", time.gmtime(time.time()))}]
        self.writeList(tmp_list)

    def writeEndTime(self):
        tmp_list = [{'EndTime': time.strftime("%d %b %Y %H:%M:%S", time.gmtime(time.time()))}]
        self.writeList(tmp_list)

    def writeNodeInfo(self, nbi_obj, node_name):
        tmp_node = node.Node(node_name)
        info_list = []
        info_list.append({'NetspanVersion': nbi_obj.getNmsVersion()})
        tmp_node.updateNodeInfo(nbi_obj)
        tmp_node.updateProvisionInfo(nbi_obj)
        info_list.append({'RelaySoftware': tmp_node.node_info['SoftwareVersion'][1]})
        info_list.append({'EnbSoftware': tmp_node.node_info['SoftwareVersion'][0]})
        info_list.append({'NodeName': tmp_node.provision_info['Name'][0]})
        info_list.append({'Hardware': tmp_node.provision_info['Hardware'][0]})
        info_list.append({'RelaySDP': tmp_node.provision_info['SystemDefaultProfile'][0]})
        info_list.append({'EnbSDP': tmp_node.provision_info['SystemDefaultProfile'][1]})
        self.writeList(info_list)


# path_to_test_config = 'C:\Users\klubelski\Desktop\LOGS\TestConfigInfo.csv'
# test_config_infog = TestConfigInfo(path_to_test_config)
# test_config_infog.writeTestName('TestowySkrypt')
# test_config_infog.writeStartTime()
#
# # utowrzenie obiektu do połączenia z netspanem i weryfikacja wersji Netspana
# netspan = nbi('10.70.6.102', '15.5', 'krystian', 'test1234')
# print ('Netspan version: %s'% netspan.getNmsVersion())
#
#
# test_config_infog.writeNodeInfo(netspan, 'Poland_SVG_AU545_205')


