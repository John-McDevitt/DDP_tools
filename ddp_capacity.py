#!/usr/local/bin/python3
''' standard template

 Script Name    : ddp_capacity.py
 Created        : 20241024
 Author         : John McDevitt
 Function       : Generate DDP capacities, including various ADR effective capacities
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
import math

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
    args.program_name=os.path.basename(sys.argv[0])
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



##########################################################################
## Main                                                                 ##
##########################################################################
if __name__ == '__main__':
  
    args = parse_arguments()
    log = setup_log()

    log.info(args.program_name + ' begins')
    DRIVE =[
    "3.8TB-SSD",
    "7.6TB-SSD",
    "15TB-SSD",
    "30TB-SSD",
    "60TB-SSD",
    ]
    # Drive sizes (using GB found in maint manual, converted to GiB)
    DRIVE_CAP = {
        "3.8TB-SSD" : 3521.26,
        "7.6TB-SSD" : 7042.52,
        "15TB-SSD" : 14015.00,
        "30TB-SSD" : 28028.99,
        "60TB-SSD" : 56058.00
    }
   
    ADR_OPTIONS =[
    "Compression Only",
    "Compression and Dedupe",
    "No Data Reduction",
    ]

    STRIPES =[
    "14+2",
    "6+2"
    ]

    STRIPE_EFFICIENCY = {
        "14+2" : (1-(2/16)),
        "6+2" : (1-(2/8))
    }

    DDP_capacity = {}
    Eff_capacity = {}
    Pool_capacity = []
    ADR_capacity = []
    Ratios = []
    Depletion_threshold = []
    Prefered_Drive = []
    Stripe_size = []
    ADR_selection = []

    for x in range(9,33):
        log.info('drive count: ' +str(x))
        for cap in DRIVE:
            log.info('looking at ' + cap)
            for stripe in STRIPES :
                log.info('looking at stripe size ' + stripe)
                ddp_cap = 0
                if (x<17):
                    if stripe=='6+2':
                        ddp_cap = math.floor((x-1)*(DRIVE_CAP[cap])*(STRIPE_EFFICIENCY[stripe])*.98)
                else:
                    ddp_cap = math.floor((x-1)*(DRIVE_CAP[cap])*(STRIPE_EFFICIENCY[stripe])*.98)

                if ddp_cap:
                    log.warning('ddp capacity is ' +str(ddp_cap))
                    #print(f"{x} {cap} drives with {stripe} provides {ddp_cap} GiB usable")
                    DDP_capacity[str(x)+'_'+cap+'_'+stripe] = ddp_cap
    
    print("Config,DDP Capacity (GiB),90% Pool Depletion(GiB), DRD Effective supported (2:1), DRD Effective (3:1), DRD Effective (4:1), DRS Effective (2:1), DRS Effective (2.5:1), DRS Effective (3:1), DRS Effective (3.5:1), DRS Effective (4:1)")
    for config in DDP_capacity:
        log.info('working on pool size with ' + config)
        dp90 = round(DDP_capacity[config] * .9,2)
        log.info('effective capacity supported in pool with ' + str(dp90) +'TiB at 3:1')
        # effective/ratio + metadata + garbage = capacity required.  calculating effective given capacity available (dp90):
        # metadata is .03 effective, garbage is .07 (effective/ratio)
        # dp90 = (1.07 Effective/3) + .03 effective
        # dp90 - .03E = 1.07 Effective/3
        # 3dp90 - .09E = 1.07 E
        # 3dp90 = 1.16E
        # E = 3*dp90/1.16
        eff_3 = math.floor(3*dp90/1.16)
        eff_2 = math.floor(2*dp90/1.13)
        eff_4 = math.floor(4*dp90/1.19)
        drs_4 = math.floor(4*dp90/1.31)
        drs_35 = math.floor(3.5*dp90/1.28)
        drs_3 = math.floor(3*dp90/1.25)
        drs_25 = math.floor(2.5*dp90/1.22)
        drs_2 = math.floor(2*dp90/1.19)
        Eff_capacity[config]=eff_3
        print(f"{config},{DDP_capacity[config]},{dp90},{eff_2},{eff_3},{eff_4},{drs_2},{drs_25},{drs_3},{drs_35},{drs_4}")
                    

    """ log.critical('crit') # always prints
    log.error('error') # always logs
    log.warning('warn') # logs with -v
    log.info('info') # logs with -vv
    log.debug('debug') # logs with -vvv """
    log.info(args.program_name + ' ends')
