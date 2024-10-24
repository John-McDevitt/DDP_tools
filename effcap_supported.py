#!/usr/local/bin/python3
''' standard template

 Script Name    : effcap_supported.py
 Created        : 20240924
 Author         : John McDevitt
 Function       : provide effective capacity support for given usable
                :
 Usage          : 
 Update Log     :

'''

##########################################################################
## Imports                                                              ##
##########################################################################
import logging 
import logging.handlers
import argparse
import sys
import os
from tkinter import *
from tkinter import messagebox
from tkinter import ttk

##########################################################################
## Function definitions                                                 ##
##########################################################################
def parse_arguments():
    ''' argument object

    this is standard argument parsing.  add your required args below
    '''

    parser = argparse.ArgumentParser()
    parser.add_argument('-v', "--verbose", action='count',default=0)
    parser.add_argument("--logfile", type=str)
    args = parser.parse_args()
    args.program_name=sys.argv[0]
    return args

def setup_log():
    ''' log object

    Enable logging for the script utilizing the -v for verbose arguments
    log.critical('crit') # always prints
    log.error('error') # always logs
    log.warning('warn') # logs with -v
    log.info('info') # logs with -vv
    log.debug('debug') # logs with -vvv
    '''

    # capture all log messages to the log files if provided
    loglevel=logging.DEBUG

    logformat='%(asctime)s %(name)s %(funcName)s %(levelname)s line: %(lineno)d %(message)s'
    log = logging.getLogger(args.program_name)
    log.setLevel(loglevel)
    if args.logfile is None:
        if 'LOGFILE' in os.environ:
            if os.path.isdir(os.environ['LOGFILE']):
                fh = logging.handlers.TimedRotatingFileHandler(os.path.join(os.environ['LOGFILE'],args.program_name + ".log"),'D',1,3)
            else:
                fh = logging.handlers.TimedRotatingFileHandler(os.environ['LOGFILE'],'D',1,3)
            fh.setLevel(loglevel)
            fh.setFormatter(logging.Formatter(logformat))
    elif os.path.isdir(args.logfile):
        fh = logging.handlers.TimedRotatingFileHandler(os.path.join(args.logfile,args.program_name + ".log"),'D',1,3)
    else:
        fh = logging.handlers.TimedRotatingFileHandler(args.logfile,'D',1,3)
        
    if args.logfile or ('LOGFILE' in os.environ):
        fh.setLevel(loglevel)
        fh.setFormatter(logging.Formatter(logformat))
        log.addHandler(fh)
    
    # only log to the console if using -v
    if args.verbose == 1:
        loglevel = logging.WARNING
    elif args.verbose == 2:
        loglevel = logging.INFO
    elif args.verbose > 2:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.ERROR
    
    ch = logging.StreamHandler()
    ch.setLevel(loglevel)
    ch.setFormatter(logging.Formatter(logformat))
    log.addHandler(ch)

    return(log)

def terminate(event=''):
    sys.exit()

def calculate(event=''):
    log.info("in calculate with %s usable and %s" %(useable_cap.get(),attainment_ratio.get()))
    # effective/ratio + metadata + garbage = capacity required.  calculating effective given capacity available
    # garbage is 7% of effective/ratio
    # DRS metadata is 6% of effective
    # usable = (1.07 * effective / ratio) + 0.06 * effective
    # effective = ratio * usable / ((ratio * 0.06) + 1.07)
    effective = attainment_ratio.get() * useable_cap.get() / ((attainment_ratio.get() * 0.06) + 1.07)
    ttk.Label(window,text="Effective Capacity", width=20).grid(row=3,column=0,sticky=W)
    ttk.Label(window,text=str(round(effective,2))).grid(row=3,column=1)
    



##########################################################################
## Main                                                                 ##
##########################################################################
if __name__ == '__main__':
  
    args = parse_arguments()
    log = setup_log()

    log.info(args.program_name + ' begins')

    ADR_OPTIONS =[
    "Compression Only",
    "Compression and Dedupe"
    ]

    window = Tk()
    window.title("DDP pool configurator - v1.7")
    window.bind("q",terminate)
    window.bind("<Return>",calculate)

    useable_cap=DoubleVar()
    attainment_ratio=DoubleVar()
    effecitve_cap=DoubleVar()
    useable_cap.set(100)
    attainment_ratio.set(4.0)

    ttk.Label(window,text="Usable Capacity", width=20).grid(row=1,column=0,sticky=W)
    ttk.Label(window,text="Attainment Ratio", width=20).grid(row=2,column=0,sticky=W)
    ttk.Label(window,text="Effective Capacity", width=20).grid(row=3,column=0,sticky=W)
    ttk.Entry(window,textvariable=useable_cap,width=6).grid(row=1,column=1,sticky=E)
    ttk.Entry(window,textvariable=attainment_ratio,width=6).grid(row=2,column=1,sticky=E)
    ttk.Button(window,text="Calculate",command=calculate).grid(row=4,columnspan=2)

    window.mainloop()

    
    log.critical('crit') # always prints
    log.error('error') # always logs
    log.warning('warn') # logs with -v
    log.info('info') # logs with -vv
    log.debug('debug') # logs with -vvv
    log.info(args.program_name + ' ends')
