import os
import errno
import threading


MAX_REBOOT_COUNTER = 5
LOG_PATH = '/home/airspan/Desktop/PythonResults/Log/LogReboot'

#Sprawdzenie czy sciezka istnieje, jesli nie to utworzenie odpowiednich katalogow
if not os.path.exists(os.path.dirname(LOG_PATH)):
    try:
        os.makedirs(os.path.dirname(LOG_PATH))
    except OSError as exc:  #Guard against race condition
        if exc.errno != errno.EEXIST:
            raise

# for i in range(MAX_REBOOT_COUNTER):
#     file_r = open('%s%i.log'%(LOG_PATH,i+1), "w")  # tworzenie pliku wynikowego
#     file_r.write("Reboot Number: %i"%(i+1))
#     file_r.close()

#to samo co wyzej tylko za pomoca komendy with, dzieki niej nie trzeba zamykac pliku. Komenda zrobi to za nas
for i in range(MAX_REBOOT_COUNTER):
    file_log_name = '%s%i.log'%(LOG_PATH,i+1)
    print file_log_name
    with open (file_log_name,'w') as file_r:
        file_r.write("Reboot Number: %i" % (i + 1))

def serialToFile