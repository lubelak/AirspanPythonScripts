import paramiko
import os
import platform
import time
import re

RESULTS_PATH = "/home/airspan/Desktop/TestResult.csv"

file_r = open(RESULTS_PATH, "w")
file_r.write("Dziala")
file_r.close()


# test_str = "'./tnet\r\nStart connection to DGS...\r\nConnected to DGS server\r\n[ft] tnet > \r\x1b[K[ft] tnet > '"
# print test_str.find("tnet >")
# print test_str.find("tnet")
# if test_str.find("tnet >") == 2  :
#     print "znaleziono znak zachty"
# else:
#     print "Brak znaku zachety"
#
# if test_str.find("tnet") == 2  :
#     print "znaleziono znak zachty"
# else:
#     print "Brak znaku zachety"