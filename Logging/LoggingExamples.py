import logging

# set up logging to file - see previous section for more details
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-8s %(levelname)-8s %(message)s',
                    datefmt='%d-%m-%y %H:%M:%S',
                    filename='/home/airspan/Desktop/PythonResults/MainLog.log',
                    filemode='w')

# define a Handler which writes INFO messages or higher to the sys.stderr
console = logging.StreamHandler()
console.setLevel(logging.INFO)
# set a format which is simpler for console use
formatter = logging.Formatter('%(asctime)s %(name)-8s: %(levelname)-10s %(message)s','%d-%m-%y %H:%M:%S')
# tell the handler to use this format
console.setFormatter(formatter)
# add the handler to the root logger
logging.getLogger('').addHandler(console)

# Now, we can log to the root logger, or any other logger. First the root...
logging.debug('Pierwszy wpis logowania')
logging.critical('Pierwszy wpis logowania')


#Dzieki powyzszemu wszystkie wiadomosci DEBUG i wyzej sa logowane do pliku rowniez te z roznych pakietow/bibliotek zaimporotwanych
#Wszystkie wiadomosci INFO i wyzej sa wyrzucane na konsole, dzieki temu konsola nie jest bardzo zaśmiecona
#aby cos teraz wyswietlic na konsoli i rowniez dodac ten wpis do pliku nalezy uzyc komendy ponizej:
#logging.info('Wrzucam cos na konsole i jednoczesnie do pliku')


#Logging LEVEL
# CRITICAL
# ERROR
# WARNING
# INFO
# DEBUG
# UNSET

#https://docs.python.org/2/howto/logging-cookbook.html