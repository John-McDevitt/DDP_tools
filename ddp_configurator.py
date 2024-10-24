#!/usr/local/bin/python3
''' 

Script Name    : ddp_configurator.py
Created        : 20230124_1520
Author         : John McDevitt
Function       : Takes effective capacity inputs and generates DDP config
               :
Usage          : takes no input
Update Log     : version 1.0
               : version 1.1 small formatting updates, default values
               : 20230211 version 1.2 14+2 support
               : 20230211 v 1.3 Significant logic correction for parity
                 Had been incorrectly using 2 parity drives as fixed value
                 and not accounting for stripe size
               : v 1.4 added selection for 6+2 or 14+2
               : v1.5 20230213 change stripe to drop down.  change ADR selections to drop down
               : v1.5.1 20230215 fix 32 drive DDP reporting as 1 partial
               : balance drive counts across the configured DDPs
               : v1.6 20230213 should limit capacities.  3PiB for a pool, maybe prompt for array type and limit effective capacity
               : v1.7 20230309 multiple pools, better output window, internal redesign
               : v1.8 20240505 DRD and DRS.  only journals w/o ADR
To Dos         : Include multi-CBX options
               : Include relative pricing
               : Anchor results windows 
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
from tkinter import *
from tkinter import messagebox
from tkinter import ttk

##########################################################################
## Function definitions                                                 ##
##########################################################################
def parse_arguments():
    ''' 
    argument object

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

    if args.verbose == 1:
        loglevel = logging.WARNING
    elif args.verbose == 2:
        loglevel = logging.INFO
    elif args.verbose > 2:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.ERROR
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
    else:
        ch = logging.StreamHandler()
        ch.setLevel(loglevel)
        ch.setFormatter(logging.Formatter(logformat))
        log.addHandler(ch)
    return(log)

def terminate(event=''):
    sys.exit()

def calculate(event=''):
    def balance(d_count,ddp_count):
        log.info("in balance with " + str(d_count) + " " + str(ddp_count))
        ddp_dict = {}
        for k in range(ddp_count):
            log.info("basic populating ddp dict with key " + str(k))
            ddp_dict[k]=0

        best_fit = d_count//ddp_count
        log.info("best fit drive count is " + str(best_fit))
        ddp_dict = dict.fromkeys(ddp_dict,best_fit)
        for l in range(d_count%ddp_count):
            log.info('add one of the leftover drives to ddp ' + str(l))
            ddp_dict[l]+=1
        log.info(ddp_dict)
        return(ddp_dict)
    
    def calc_ddp(pool_size):
        match Stripe_size[i].get():
            case "14+2":
                log.info('using 14+2')
                DATA_STRIPE = 14
                PARITY_STRIPE = 16
                EFFICIENCY = .875
            case "6+2":
                log.info("using 6+2")
                DATA_STRIPE = 6
                PARITY_STRIPE = 8
                EFFICIENCY = .75
            case _:
                log.info('only raid 6 today...')
        
        log.info('calc_ddp with ' + str(pool_size))
        required_drives = math.ceil(pool_size*1024/DRIVE_CAP[Prefered_Drive[i].get()]/EFFICIENCY)
        log.info('minimum required drives, with parity but not spare space, for pool is ' + str(required_drives))
        DDPs = {}
        if required_drives < PARITY_STRIPE:
            log.info("padding required drives to match stripe with parity")
            required_drives = PARITY_STRIPE
        log.info("calling balance")
        DDPs=balance(required_drives,(required_drives//31)+1)
        configured_drives = required_drives + (required_drives//31)+1
        log.info('configured drives is required drives plus one for each DDP for spare capacity ' +str(configured_drives))
        ttk.Label(results,text=str(configured_drives),foreground="orange").grid(row=10,column=1)
        ddp_capacity = required_drives * DRIVE_CAP[Prefered_Drive[i].get()]/1024*EFFICIENCY
        log.info("required drives " +str(required_drives) + " ddp capacity " + str(ddp_capacity))
        ttk.Label(results,text=str(round(ddp_capacity,2)),foreground="green").grid(row=8,column=1)
                
        max_usable_capacity = ddp_capacity*(Depletion_threshold[i].get()/100)
        log.info('pool will have usable capacity (under depletion threshold) of: ' + str(max_usable_capacity))
        
        if DRD_capacity[i].get() > 0:
            max_effective_capacity = round((max_usable_capacity-garbage-metadata)*Ratios[i].get(),2)
        else:
            max_effective_capacity = round(max_usable_capacity,2)
        log.info('which yields an ADR max effective of: ' + str(max_effective_capacity))
        ttk.Label(results,text=str(max_effective_capacity),foreground="red").grid(row=9,column=1)
        return(DDPs)
  
    def calc_raid(pool_size):
        match Stripe_size[i].get():
            case "14+2":
                log.info('using 14+2')
                DATA_STRIPE = 14
                PARITY_STRIPE = 16
                EFFICIENCY = .875
            case "6+2":
                log.info("using 6+2")
                DATA_STRIPE = 6
                PARITY_STRIPE = 8
                EFFICIENCY = .75
            case _:
                log.info('only raid 6 today...')
        log.info('calc_raid with ' + str(pool_size))
        required_drives = math.ceil(pool_size*1024/DRIVE_CAP[Prefered_Drive[i].get()])
        log.info('required drives ' + str(required_drives))
        pg_count = math.ceil(required_drives/DATA_STRIPE)
        log.info('PG count is ' +str(pg_count))
        max_usable_capacity = pg_count*DATA_STRIPE*DRIVE_CAP[Prefered_Drive[i].get()]/1024*(Depletion_threshold[i].get()/100)
        log.info('working max cap ' + str(max_usable_capacity))
        if DRD_capacity[i].get() > 0:
            max_effective_capacity = round((max_usable_capacity-garbage-metadata)*Ratios[i].get(),2)
        else:
            max_effective_capacity = round(max_usable_capacity,2)
        log.info('which yields an ADR max effective of: ' + str(max_effective_capacity))       
        log.info('RAID pool will have usable capacity (under depletion threshold) of : ' + str(max_usable_capacity))
        log.info('minimum required data drives for pool is ' + str(required_drives))
        log.info('minimum number of parity groups is ' + str(math.ceil(required_drives/DATA_STRIPE)))
        log.info('total PG drive count is ' + str((math.ceil(required_drives/DATA_STRIPE)*PARITY_STRIPE)))
        log.info('recommended spares (one for each 32 drives) ' + str((math.ceil(required_drives/DATA_STRIPE)*PARITY_STRIPE)//32 + 1))
        ttk.Label(results,text=str(round(pg_count*DATA_STRIPE*DRIVE_CAP[Prefered_Drive[i].get()]/1024,2)),foreground="green").grid(row=15+d,column=1)
        ttk.Label(results,text=str(max_effective_capacity),foreground="red").grid(row=16+d,column=1)
        ttk.Label(results,text=str((math.ceil(required_drives/DATA_STRIPE)*PARITY_STRIPE)),foreground="orange").grid(row=17+d,column=1)
        ttk.Label(results,text=str((math.ceil(required_drives/DATA_STRIPE)*PARITY_STRIPE)//32 + 1),foreground="orange").grid(row=18+d,column=1)
        ttk.Label(results,text=str(pg_count)).grid(row=19+d,column=1)
        
        return()
    
    log.info('in calculate')
    log.info('number of pools is ' + str(pool_count))
    for i in range(pool_count):
        log.debug('i is ' + str(i))
        log.info('DRD effcap of pool is ' + str(DRD_capacity[i].get()))
        log.info('DRS effcap of pool is ' + str(DRS_capacity[i].get()))
        log.info('JNL cap of pool is ' + str(JNL_capacity[i].get()))
        # if Pool_capacity[i].get() < DRD_capacity[i].get():
        #     messagebox.showerror('Capacity mismatch','The Total Customer Data includes ADR data\nIt must be greater than or equal to the ADR value')
        #     return
        # else:
        #     HDP_cap = Pool_capacity[i].get() - DRD_capacity[i].get()
        #     log.info('HDP portion of capacity is ' + str(HDP_cap))
        # if Pool_capacity[i].get() > 3000:
        #     messagebox.showerror('Pool capacity','HDP pool built on internal drives limited to ~3PiB')
        #     return
        if Depletion_threshold[i].get()/100 < .8:
            messagebox.showerror('Depletion threshold','Depletion threshold should be between 80 and 100%')
            return
        elif Depletion_threshold[i].get()/100 > 1:
            messagebox.showerror('Depletion threshold','Depletion threshold should be between 80 and 100%')
            return
        
        log.info('checking ADR selection with ' + str(ADR_selection[i].get()))
        match ADR_selection[i].get():
            case "No Data Reduction":
                garbage=0
                metadata = 0.0
                if DRD_capacity[i].get() > 0:
                    messagebox.showerror("ADR mismatch","'No Data Reduction' set, but ADR capacity present")
                    return 
            case "Compression Only":
                log.info('Compression only -- metadata calculation is 0.02 of DRD cap and 0.04 of DRS cap')
                metadata = (float(DRD_capacity[i].get()) * 0.02) + (float(DRS_capacity[i].get()) * 0.04)
                garbage = (float(DRD_capacity[i].get())+float(DRS_capacity[i].get()))/float(Ratios[i].get()) * 0.07
            case "Compression and Dedupe":
                log.info('Comp and Deduupe metadata calculations is 0.03 of DRD cap and 0.06 of DRS cap')
                metadata = (float(DRD_capacity[i].get()) * 0.03) + (float(DRS_capacity[i].get()) * 0.06)
                garbage = float(DRD_capacity[i].get())/float(Ratios[i].get()) * 0.07
        
        log.info('required pool capacity is (JNL capacity + (ADR effective capacities / ADR ratio) + metadata + garbage)/depletion threshold')
        log.debug('(' +str(JNL_capacity[i].get()) + ' + (' + str(DRD_capacity[i].get()) + '+ ' + str(DRS_capacity[i].get()) + ' / ' + str(Ratios[i].get()) + ') + ' + str(metadata) + ' + ' + str(garbage) + ' )/ ' + str(Depletion_threshold[i].get()/100))
        pool_size = round((JNL_capacity[i].get()+((DRD_capacity[i].get() + DRS_capacity[i].get())/Ratios[i].get())+metadata+garbage)/(Depletion_threshold[i].get()/100),2)
        log.info("Pool size is " + str(pool_size))

        results = Tk()
        results.title("Pool configuration options")
        results.geometry('+%s+%s' %(window.winfo_x()+400, window.winfo_y()))
        results.bind("q",lambda x: results.destroy())
        ttk.Label(results,text="Stripe size: ").grid(row=0,column=0)
        match Stripe_size[i].get():
            case "14+2":
                ttk.Label(results,text="14+2").grid(row=0,column=1)
            case "6+2":
                ttk.Label(results,text="6+2").grid(row=0,column=1)
        ttk.Label(results,text="Drive size (TiB): ").grid(row=1,column=0)
        ttk.Label(results,text=str(Prefered_Drive[i].get())).grid(row=1,column=1)
        ttk.Label(results,text="Pool size required (TiB): ").grid(row=2,column=0)
        ttk.Label(results,text=str(pool_size),foreground="green").grid(row=2,column=1)
        ttk.Label(results,text="Total Effective requested(TiB): ").grid(row=3,column=0)
        ttk.Label(results,text=str(DRD_capacity[i].get()+DRS_capacity[i].get()),foreground="red").grid(row=3,column=1)
        ttk.Label(results,text="Journal space requested(TiB): ").grid(row=4,column=0)
        ttk.Label(results,text=str(JNL_capacity[i].get()),foreground="red").grid(row=4,column=1)
        ttk.Separator(results,orient="horizontal").grid(row=5,columnspan=2,sticky="ew")
        ttk.Label(results,text="---DDP Configuration---").grid(row=6,columnspan=2,sticky="ew")
        ttk.Separator(results,orient="horizontal").grid(row=7,columnspan=2,sticky="ew")
        ttk.Label(results,text="Pool size configured (TiB): ").grid(row=8,column=0)
        ttk.Label(results,text="Effective supported(TiB): ").grid(row=9,column=0)
        ttk.Label(results,text="Total DDP drives configured: ").grid(row=10,column=0)
        
        DDPs={}
        log.info('calling calc_ddp with ' + str(pool_size))
        DDPs=calc_ddp(pool_size)
        
        for d in DDPs:
            DDPs[d]+=1
            ttk.Label(results,text='DDP ' + str(d+1) + ' drive count:').grid(row=(11+d),column=0)
            ttk.Label(results,text=str(DDPs[d])).grid(row=(11+d),column=1)
        log.info("balanced drive config is : " + str(DDPs))
        
        ttk.Separator(results,orient="horizontal").grid(row=12+d,columnspan=2,sticky="ew")
        ttk.Label(results,text="---RAID PG Configuration---").grid(row=13+d,columnspan=2,sticky="ew")
        ttk.Separator(results,orient="horizontal").grid(row=14+d,columnspan=2,sticky="ew")
        ttk.Label(results,text="Pool size configured (TiB): ").grid(row=15+d,column=0)
        ttk.Label(results,text="Effective supported(TiB): ").grid(row=16+d,column=0)
        ttk.Label(results,text="Total PG drives configured: ").grid(row=17+d,column=0)
        ttk.Label(results,text="Recommended Spare Drives: ").grid(row=18+d,column=0)
        log.info('calling calc_raid with ' + str(pool_size))
        calc_raid(pool_size)
        match Stripe_size[i].get():
            case "14+2":
                ttk.Label(results,text="Traditional RAID 14+2 PGs: ").grid(row=19+d,column=0)
            case "6+2":
                ttk.Label(results,text="Traditional RAID 6+2 PGS: ").grid(row=19+d,column=0)
    
def add_pool(row_count):
    global active_row
    global pool_count
    global Pool_capacity
    global DRD_capacity
    global DRS_capacity
    global Ratios
    global Depletion_threshold
    global Prefered_Drive
    global Stripe_size
    global ADR_selection
    
    active_row += 9
    
    log.info("in add_pool with row count " + str(row_count) + " and pool count " + str(pool_count))
    if pool_count > 0:
        ttk.Separator(window,orient="horizontal").grid(row=row_count,columnspan=2,sticky="ew")
    pool_count += 1
    if pool_count >3:
        log.info('too many pools')
        messagebox.showwarning('Pools','Currently supporting up to 3 pools')
        return()
    
    ttk.Label(window,text="DRD effective capacity (TiB):").grid(row=row_count+1,column=0,sticky=W)
    ttk.Label(window,text="DRS effective capacity (TiB):").grid(row=row_count+2,column=0,sticky=W)
    ttk.Label(window,text="ADR ratio (for 4:1 enter 4):").grid(row=row_count+3,column=0,sticky=W)
    ttk.Label(window,text="HDP Depletion threshold (90 for 90%)").grid(row=row_count+4,column=0,sticky=W)
    ttk.Label(window,text="HUR JNL Capacity (TiB):").grid(row=row_count+5,column=0,sticky=W)
    ttk.Label(window,text="DRIVE TYPE").grid(row=row_count+6, column=0,sticky=W)
    ttk.Label(window,text="Stripe configuration").grid(row=row_count+7,column=0,sticky=W)
    ttk.Label(window,text="Data Reduction Selection").grid(row=row_count+8,column=0,sticky=W)
    
    # Total_Cap=DoubleVar()
    # Total_Cap.set(500)
    # ttk.Entry(window,textvariable=Total_Cap,width=4).grid(row=row_count+1,column=1,sticky=E)
    # Pool_capacity.append(Total_Cap)
   
    DRD_Eff_Cap=DoubleVar()
    DRD_Eff_Cap.set(500)
    ttk.Entry(window,textvariable=DRD_Eff_Cap,width=4).grid(row=row_count+1,column=1,sticky=E)
    DRD_capacity.append(DRD_Eff_Cap)
   
    DRS_Eff_Cap=DoubleVar()
    DRS_Eff_Cap.set(400)
    ttk.Entry(window,textvariable=DRS_Eff_Cap,width=4).grid(row=row_count+2,column=1,sticky=E)
    DRS_capacity.append(DRS_Eff_Cap)
    
    ratio=DoubleVar()
    ratio.set(4.0)
    ttk.Entry(window,textvariable=ratio,width=4).grid(row=row_count+3,column=1,sticky=E)
    Ratios.append(ratio)
   
    Depletion=IntVar()
    Depletion.set(90)
    ttk.Entry(window,textvariable=Depletion,width=4).grid(row=row_count+4,column=1,sticky=E)
    Depletion_threshold.append(Depletion)
   
    JNL_Cap=DoubleVar()
    JNL_Cap.set(10)
    ttk.Entry(window,textvariable=JNL_Cap,width=4).grid(row=row_count+5,column=1,sticky=E)
    JNL_capacity.append(JNL_Cap)

    preferred_drive_var= StringVar()
    preferred_drive_var.set('30TB-SSD') 
    OptionMenu(window, preferred_drive_var,*DRIVE).grid(row=row_count+6,column=1,sticky=EW)
    Prefered_Drive.append(preferred_drive_var)
   
    stripe_size_var = StringVar()
    stripe_size_var.set('6+2')
    OptionMenu(window,stripe_size_var,*STRIPES).grid(row=row_count+7,column=1,sticky=EW)
    Stripe_size.append(stripe_size_var)
   
    ADR_selection_var = StringVar()
    ADR_selection_var.set("Compression and Dedupe")
    OptionMenu(window,ADR_selection_var,*ADR_OPTIONS).grid(row=row_count+8,column=1,sticky=EW)
    ADR_selection.append(ADR_selection_var)

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
    ]
    # Drive sizes (using GB found in maint manual, converted to GiB)
    DRIVE_CAP = {
        "3.8TB-SSD" : 3521.26,
        "7.6TB-SSD" : 7042.52,
        "15TB-SSD" : 14015.00,
        "30TB-SSD" : 28028.99
    }
   
    ADR_OPTIONS =[
    "Compression Only",
    "Compression and Dedupe"
    ]

    STRIPES =[
    "14+2",
    "6+2"
    ]


    #Pool_capacity = []
    DRD_capacity = []
    DRS_capacity = []
    Ratios = []
    Depletion_threshold = []
    JNL_capacity = []
    Prefered_Drive = []
    Stripe_size = []
    ADR_selection = []
    
    window = Tk()
    window.title("DDP pool configurator - v1.7")
    window.bind("q",terminate)
    window.bind("<Return>",calculate)
    
    active_row = 0
    pool_count = 0
    add_pool(active_row)
    log.info('row and pool count ' + str(active_row) + ' ' + str(pool_count))
    ttk.Button(window,text="Add pool", width=6,command=lambda: add_pool(active_row)).grid(row=32,column=0,sticky=EW)
    ttk.Button(window,text="Configure", width=6,command=calculate).grid(row=32,column=1,sticky=EW)
    
    window.mainloop()
    #log.warning('warn') # logs with -v
    #log.info('info') # logs with -vv
    #log.debug('debug') # logs with -vvv
    log.info(args.program_name + ' ends')
