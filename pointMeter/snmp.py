# -*- coding: utf-8 -*-

import logging
from pysnmp.entity.rfc3413.oneliner import cmdgen


# SNMP_HOST = '192.168.15.1'             #adres lokalny FT, po IPv6 nie mozna bylo pobrac informacji po snmp
# SNMP_HOST = '10.11.40.1'


class SnmpManager():
    def __init__(self, host, port=161, community='public'):
        self.host = host
        self.port = port
        self.community = community
        self.net_info = {}

    def snmpget(self, oid):
        errorIndication, errorStatus, errorIndex, \
        varBinds = cmdgen.CommandGenerator().getCmd(
            cmdgen.CommunityData(self.community),
            cmdgen.UdpTransportTarget((self.host, self.port)),
            oid
        )
        for name, val in varBinds:
            logging.info(oid + ': ' + val.prettyPrint())
            return str(val.prettyPrint())

    def updateNetInfo(self):
        self.net_info['RSRP0'] = self.snmpget('1.3.6.1.4.1.17713.20.2.1.2.6.0')
        self.net_info['RSRP1'] = self.snmpget('1.3.6.1.4.1.17713.20.2.1.2.7.0')
        self.net_info['CINR0'] = self.snmpget('1.3.6.1.4.1.17713.20.2.1.2.9.0')
        self.net_info['CINR1'] = self.snmpget('1.3.6.1.4.1.17713.20.2.1.2.10.0')
        self.net_info['RSRQ'] = self.snmpget('1.3.6.1.4.1.17713.20.2.1.2.8.0')
        self.net_info['PCI'] = self.snmpget('1.3.6.1.4.1.17713.20.2.1.2.18.0')

    def getNetInfo(self):
        self.updateNetInfo()
        return self.net_info

#
# snmp_m = snmpManager(SNMP_HOST)
# snmp_m.updateNetInfo()
# print snmp_m.net_info