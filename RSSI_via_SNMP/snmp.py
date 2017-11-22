# -*- coding: utf-8 -*-
from pysnmp.hlapi import *
import os
import platform
import time
from pysnmp.entity.rfc3413.oneliner import cmdgen

SNMP_COMMUNITY = 'public'
SNMP_PORT = 161
SNMP_HOST = '10.18.0.210'
SNMP_HOST6 = 'fe80::c6ed:baff:fea3:0482'

#Poniższy kod zwraca cała tabele parametrow z FT odnosnie rssi, rejestracji itd.


# errorIndication, errorStatus, errorIndex, \
# varBindTable = cmdgen.CommandGenerator().bulkCmd(
#             cmdgen.CommunityData(SNMP_COMMUNITY),
#             cmdgen.Udp6TransportTarget((SNMP_HOST6, SNMP_PORT)),
#             # cmdgen.UdpTransportTarget((SNMP_HOST, SNMP_PORT)),
#             0,
#             25,
#             (1,3,6,1,4,1,989,1,21,1,3,6)                              #MIB Table asIbFtDiagDiagTable
#             # (1,3,6,1,2,1,4,20), # ipAddrTable OID . This works fine.
#             # (1,3,6,1,2,1,4,21), # ipRouteTable
#             # (1,3,6,1,2,1,4,22), # ipNetToMediaTable
#         )
#
# if errorIndication:
#    print errorIndication
# else:
#     if errorStatus:
#         print '%s at %s\n' % (
#             errorStatus.prettyPrint(),
#             errorIndex and varBindTable[-1][int(errorIndex)-1] or '?'
#             )
#     else:
#         for varBindTableRow in varBindTable:
#             for name, val in varBindTableRow:
#                 print '%s = %s' % (name.prettyPrint(), val.prettyPrint())


################ MOJE ###########################
# #Jesli potrzeba konkretnej wartosci- inforamcji o konkretnym parametrze to nalezy uzyc kodu ponizej
# errorIndication, errorStatus, errorIndex, \
# varBinds = cmdgen.CommandGenerator().getCmd(
#             cmdgen.CommunityData(SNMP_COMMUNITY),
#             cmdgen.Udp6TransportTarget((SNMP_HOST6, SNMP_PORT)),
#             '1.3.6.1.4.1.989.1.21.1.3.6.1.15.1'
#             # (1,3,6,1,2,1,4,20), # ipAddrTable OID . This works fine.
#             # (1,3,6,1,2,1,4,21), # ipRouteTable
#             # (1,3,6,1,2,1,4,22), # ipNetToMediaTable
#         )
#
# # print varBinds
# for name, val in varBinds:
#     print ('%s = %s' %(name.prettyPrint(), val.prettyPrint()))
#
# for name, val in varBinds:
#     print type(val.prettyPrint())
#     if val.prettyPrint() == 'RegistrationComplete8':
#         print "działa porównanie 1"
#     elif str(val.prettyPrint()) == 'RegistrationComplete':
#         print "dziala porownanie 2"
#     else:
#         print "nic nie dziala"
#     #return val.prettyPrint()
#
# print time.strftime("%c")


################ MOJE 2###########################
errorIndication, errorStatus, errorIndex, \
varBindTable = cmdgen.CommandGenerator().bulkCmd(
            cmdgen.CommunityData(SNMP_COMMUNITY),
            cmdgen.UdpTransportTarget((SNMP_HOST, SNMP_PORT)),
            # cmdgen.UdpTransportTarget((SNMP_HOST, SNMP_PORT)),
            0,
            25,
            # (1,3,6,1,4,1,989,1,21,1,3,6),                              #MIB Table asIbFtDiagDiagTable
            (1,3,6,1,4,1,989,1,16,2,9,8)
            # (1,3,6,1,2,1,4,20), # ipAddrTable OID . This works fine.
            # (1,3,6,1,2,1,4,21), # ipRouteTable
            # (1,3,6,1,2,1,4,22), # ipNetToMediaTable
        )

if errorIndication:
   print errorIndication
else:
    if errorStatus:
        print '%s at %s\n' % (
            errorStatus.prettyPrint(),
            errorIndex and varBindTable[-1][int(errorIndex)-1] or '?'
            )
    else:
        for varBindTableRow in varBindTable:
            for name, val in varBindTableRow:
                print '%s = %s' % (name.prettyPrint(), val.prettyPrint())

