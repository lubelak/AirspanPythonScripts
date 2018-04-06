# -*- coding: utf-8 -*-


#AU image upgrade script. Author: Krystian Lubelski

import nbi, time ,datetime, re , random, sys, os
import logging
from nbi import Argstruct, nbi

class Node(object):
    """"Klasa przechowujaca i aktualizujaca dane o Node z Netspana"""
    def __init__(self, name):
        self.node_name = name
        logging.info('utworzono obiekt Node z nazwa: %s' % name)
        self.node_software_status = {}
        self.node_info = {}
        self.provision_info = {}

    def updateNodeInfo(self, nbi_obj):
        cliArgs = Argstruct({'values': ['NodeName=' + self.node_name], 'delEmpty': True})
        xml = nbi_obj.applyAndPost('Inventory', 'NodeInfoGet', cliArgs)
        self.node_info = nbi_obj.getFieldList(xml, ['Name',
                                            'NodeId',
                                            'HardwareType',
                                            'HardwareTypeId',
                                            'HardwareCategory',
                                            'HardwareCategoryId',
                                            'ProductCode',
                                            'ProductDescription',
                                            'HardwareMacAddress',
                                            'SerialNumber',
                                            'Imei',
                                            'Imsi',
                                            'Site',
                                            'Region',
                                            'Latitude',
                                            'Longitude',
                                            'Altitude',
                                            'WifiStatusMacAddress',
                                            'WifiStatusIpAddress',
                                            'IsPnpComplete',
                                            'ConnectionState',
                                            'SoftwareVersion',
                                            'StandByVersion',
                                            'ActualOperationalStatus',
                                            'RequestedOperationalStatus'])

    def updateProvisionInfo(self, nbi_obj):
        cliArgs = Argstruct({'values': ['NodeName=' + self.node_name], 'delEmpty': True})
        xml = nbi_obj.applyAndPost('Lte', 'RelayEnbConfigGet', cliArgs)
        self.provision_info = nbi_obj.getFieldList(xml, ['Name',
                                                         'Hardware',
                                                         'BandwidthMhz',
                                                         'FrameConfig',
                                                         'SystemDefaultProfile'])
        # print self.provision_info

    def updateNodeSoftwareStatus(self, nbi_obj):
        cliArgs = Argstruct({'values': ['NodeName=' + self.node_name,'NodeNameOrId='+self.node_name], 'delEmpty': True})
        xml = nbi_obj.applyAndPost('Status', 'NodeSoftwareStatusGet', cliArgs)
        self.node_software_status = nbi_obj.getFieldList(xml, ['ImageType',
                                            'RunningVersion',
                                            'StandbyVersion',#nie ma o tym informacji zaraz po wysłaniu komendy o instalację
                                            'LastRequested',
                                            'NmsState',
                                            'NodeState',
                                            'LastReadFromNode'])


    def installSoftware(self, nbi_obj, image):
        logging.info('Attempting to upgrade node with image %s ', image)
        args = Argstruct({'values':['NodeName=' + self.node_name, 'Request=Activate', 'SoftwareImage=' + image], 'delempty':True})
        xml = nbi_obj.applyAndPost('Software', 'SoftwareConfigSet', args)
        error = ''.join(nbi_obj.getField(xml, 'ErrorString')) #po co ten join
        # logging.info(error)
        if 'not found' in error:
            logging.info('SW Image ', image, 'not found on Netspan. Exiting.')
            exit(1)

    def isOnline(self, nbi_obj):
        """weryfikacja czy node jest online"""
        if nbi_obj.isNodeOnline(self.node_name):
            logging.info('Node %s is online', self.node_name)
            return True
        else:
            logging.info('Node %s is offline', self.node_name)
            return False

    #funkcja sprawdzająca kiedy node się poprawnie zaktualizował i jest w stanie idle/online/InService
    def waitForIdleState(self, nbi_obj):
        #weryfikacja stanu idle airunity
        if self.node_info['HardwareCategory'][0] == 'AirUnity':
            logging.info('waitForIdleState for HardwareType = %s' % self.node_info['HardwareType'] )
            while True:
                # print self.node_software_status
                self.updateNodeSoftwareStatus(nbi_obj)
                # time.sleep(2)
                # print node_software_status
                if (len(self.node_software_status['NodeState'])==2 and len(self.node_software_status['NmsState'])==2):
                    if self.node_software_status['NodeState'][0] == 'Idle ()' and \
                        self.node_software_status['NodeState'][1] == 'Idle' and \
                        self.node_software_status['NmsState'][0] == 'Idle' and \
                        self.node_software_status['NmsState'][1] == 'Idle':
                        logging.info('Node in idle state')
                        break
                    else:
                        logging.info('Waiting for Idle State.')
                        logging.info('Current NmsState = %s' % self.node_software_status['NmsState'])
                        logging.info('Current NodeState = %s' % self.node_software_status['NodeState'])
                        time.sleep(10)
                else:
                    logging.info('Waiting for Idle State.')
                    logging.info('Current NmsState = %s' % self.node_software_status['NmsState'])
                    logging.info('Current NodeState = %s' % self.node_software_status['NodeState'])
                    time.sleep(10)


            # weryfikacja stanu online i InService
            while True:
                self.updateNodeInfo(nbi_obj)
                if (len(self.node_info['ConnectionState']) == 2 and len(self.node_info['ActualOperationalStatus']) == 1):
                    if self.node_info['ConnectionState'][0] == 'Online' and \
                        self.node_info['ConnectionState'][1] == 'Online' and \
                        self.node_info['ActualOperationalStatus'][0] == 'InService':
                        logging.info('Node in InService state')
                        break
                    else:
                        logging.info('Waiting for InService State.')
                        logging.info('Current ConnectionState = %s' % self.node_info['ConnectionState'])
                        logging.info('Current ActualOperationalStatus = %s' % self.node_info['ActualOperationalStatus'])
                        time.sleep(10)
                else:
                    logging.info('Waiting for InService State.')
                    logging.info('Current ConnectionState = %s' % self.node_info['ConnectionState'])
                    logging.info('Current ActualOperationalStatus = %s' % self.node_info['ActualOperationalStatus'])
                    time.sleep(10)
        elif self.node_info['HardwareType'][0] == 'iBridge 460' or self.node_info['HardwareType'][0] == 'iRelay 464':
            logging.info('waitForIdleState for HardwareType = %s' % self.node_info['HardwareType'])
            while True:
                self.updateNodeSoftwareStatus(nbi_obj)
                if (len(self.node_software_status['NodeState']) == 1 and len(
                        self.node_software_status['NmsState']) == 1):
                    if self.node_software_status['NodeState'][0] == 'Idle' and \
                                    self.node_software_status['NmsState'][0] == 'Idle':
                        logging.info('Node in idle state')
                        break
                    else:
                        logging.info('Waiting for Idle State.')
                        logging.info('Current NmsState = %s' % self.node_software_status['NmsState'])
                        logging.info('Current NodeState = %s' % self.node_software_status['NodeState'])
                        time.sleep(10)
                else:
                    logging.info('Waiting for Idle State.')
                    logging.info('Current NmsState = %s' % self.node_software_status['NmsState'])
                    logging.info('Current NodeState = %s' % self.node_software_status['NodeState'])
                    time.sleep(10)

            # weryfikacja stanu online i InService
            while True:
                self.updateNodeInfo(nbi_obj)
                if (len(self.node_info['ConnectionState']) == 1): # and len(
                        #self.node_info['ActualOperationalStatus']) == 1):
                    if self.node_info['ConnectionState'][0] == 'Online': # and \
                                    #self.node_info['ActualOperationalStatus'][0] == 'InService':
                        logging.info('Node in InService state')
                        break
                    else:
                        logging.info('Waiting for InService State.')
                        logging.info('Current ConnectionState = %s' % self.node_info['ConnectionState'])
                        # logging.info('Current ActualOperationalStatus = %s' % self.node_info['ActualOperationalStatus'])
                        time.sleep(10)
                else:
                    logging.info('Waiting for InService State.')
                    logging.info('Current ConnectionState = %s' % self.node_info['ConnectionState'])
                    # logging.info('Current ActualOperationalStatus = %s' % self.node_info['ActualOperationalStatus'])
                    time.sleep(10)
        else:
            logging.error('Unknown HardwareType')
            exit(1)

    def enbRfStatusGet(self,nbi_obj):
        cliArgs = Argstruct({'values': ['NodeName=' + self.node_name, 'NodeNameOrId=' + self.node_name], 'delEmpty': True})
        xml = nbi_obj.applyAndPost('Status', 'EnbRfStatusGet', cliArgs)
        enb_rf_status = nbi_obj.getFieldList(xml, ['OperationalStatus',
                                                   'ConfiguredTxPowerDbm',
                                                   'ActualTxPowerDbm'])
        return enb_rf_status

    def enbConfigGet(self, nbi_obj):
        cliArgs = Argstruct({'values': ['NodeName=' + self.node_name], 'delEmpty': True})
        xml = nbi_obj.applyAndPost('Lte', 'EnbConfigGet', cliArgs)
        enb_config = nbi_obj.getFieldList(xml, ['Name',
                                                'Hardware',
                                                'RadioProfile',
                                                'CellNumber',
                                                'SystemDefaultProfile'])
        return enb_config



    def enbConfigSet(self, nbi_obj, profile_name, cell_number):
        cliArgs = Argstruct({'values': ['NodeName=' + self.node_name, 'RadioProfile=' + profile_name, 'CellNumber=' + cell_number], 'delEmpty': True, 'delEmptySections': True})
        xml = nbi_obj.applyAndPost('Lte', 'EnbConfigSet', cliArgs)
        error = ''.join(nbi_obj.getField(xml, 'ErrorString'))  # po co ten join
        # logging.info(error)
        if 'not found' in error:
            logging.info('Radio Profile ', profile_name, 'not found on Netspan. Exiting.')
            exit(1)

    def enbStateSet(self, nbi_obj, enb_state):
        cliArgs = Argstruct({'values': ['NodeName=' + self.node_name, 'EnbState=' + enb_state], 'delEmpty': True, 'delEmptySections': True})
        # cliArgs = Argstruct({'values': ['NodeName=' + self.node_name, 'CellState=InService', 'CellNumber=1'], 'delEmpty': True, 'delEmptySections': True})
        # cliArgs = Argstruct({'values': ['NodeName=' + self.node_name,'CellState=<CellState>InService</CellState><CellNumber>1</CellNumber>'], 'delEmpty':True, 'novalues':[
        #     '/CellState']})
        #'EnbState=OutOfService',
        xml = nbi_obj.applyAndPost('Lte', 'EnbStateSet', cliArgs)
        error = ''.join(nbi_obj.getField(xml, 'ErrorString'))  # po co ten join
        # logging.info(error)
        if 'not found' in error:
            logging.info('Node ', self.node_name, 'not found on Netspan. Exiting.')
            exit(1)

    def nodeReprovision (self, nbi_obj):
        cliArgs = Argstruct({'values': ['NodeName=' + self.node_name], 'delEmpty': True})
        xml = nbi_obj.applyAndPost('Inventory', 'NodeReprovision', cliArgs)
        error = ''.join(nbi_obj.getField(xml, 'ErrorCode'))  # po co ten join
        # logging.info(error)
        if 'OK' in error:
            logging.info('Node Reprovision OK')
        else:
            logging.error('Node Reprovision FAILED')
            # exit(1)

    def nodeResetForced (self, nbi_obj):
        cliArgs = Argstruct({'values': ['NodeName=' + self.node_name], 'delEmpty': True})
        xml = nbi_obj.applyAndPost('Inventory', 'NodeResetForced', cliArgs)
        error = ''.join(nbi_obj.getField(xml, 'ErrorCode'))  # po co ten join
        # logging.info(error)
        if 'OK' in error:
            logging.info('Node Reset OK')
        else:
            logging.error('Node Reset FAILED')
            # exit(1

