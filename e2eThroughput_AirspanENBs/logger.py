# -*- coding: utf-8 -*-

import logging


def setRootLogger (path):
    # set up logging to file - see previous section for more details
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(name)-20s %(levelname)-10s %(message)s',
                        datefmt='%d-%m-%y %H:%M:%S',
                        filename= path,
                        filemode='w')

    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(asctime)s %(name)-20s: %(levelname)-10s %(message)s', '%d-%m-%y %H:%M:%S')
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger('').addHandler(console)