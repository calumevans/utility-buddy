
#!/usr/bin/env python2.7
import os
import sys
import json
import subprocess
import time
import csv
import RPi.GPIO as GPIO
import signal
import os.path
from datetime import datetime
global PreviousTime
global usageDEC
global meterList

#variable initialization
meterList = []
PreviousTime = 0

#GPIO initialization
global button
global RedLED
global greenLED
button = 21
RedLED = 23 #gpio23 for v1.0 and v2.0
greenLED = 27 #gpio24 for v1.0, gpio27 for v2.0
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(RedLED,GPIO.OUT)
GPIO.setup(greenLED,GPIO.OUT)
GPIO.setup(button, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # Set pin 10 to be an input pin, set initial value to be pulled low (OFF)

#kill any other instances that may be running
val1 = os.system("killall -KILL rtlamr")    
val2 = os.system("killall -KILL rtl_tcp")    
time.sleep(2)

#mount server location
subprocess.Popen('sudo mount -t cifs -o credentials=/etc/win-credentials //192.168.2.20/meter_tmp /home/pi/Desktop/MeterIDsShared',stdout=subprocess.PIPE, shell=True)
print("attempted mount")
time.sleep(1)

#start listening for meters
listenersproc = subprocess.Popen('rtl_tcp')


#functions

def signal_handler(sig, frame):
    GPIO.cleanup()
    sys.exit(0)

def button_pressed_callback(channel):
    print("Button pressed!")
    GPIO.output(greenLED,GPIO.LOW)
    GPIO.output(RedLED,GPIO.LOW)
    os.execl(sys.executable, sys.executable, *sys.argv)

def getRoundedTime():
    timeR = getCurrentTime()[-5:]
    dateR = getCurrentTime()[:10]
    
    if timeR[-1:] == '0' or timeR[-1:] == '1' or timeR[-1:] == '2' or timeR[-1:] == '3' or timeR[-1:] == '4':
        newTime = timeR[:-1]+"0"
    elif timeR[-1:] == '5' or timeR[-1:] == '6' or timeR[-1:] =='7' or timeR[-1:] == '8' or timeR[-1:] == '9':
        newTime = timeR[:-1]+"5"
    else:
        print("Error in getRoundedTime")    
        
    newDT = (dateR + "_" + newTime)
    
    return newDT

def csvLogger(MeterNumber,Value,Type):
    current_time = time.time()
    today = datetime.now()

    #Timestamp = today.strftime("%Y-%m-%d_%H:%M")
    Timestamp = getRoundedTime()
    filename = "/home/pi/Desktop/MeterIDsShared/"+str(MeterNumber)+".csv"
    try:
        csvfile = open(filename, 'a', newline ='', encoding='utf-8')
        c = csv.writer(csvfile)
        data_to_save = [Timestamp, Value,Type]
        c.writerow(data_to_save)
        csvfile.close()
    except:
        csvfile = open(filename, 'w', newline ='',encoding='utf-8')
        c = csv.writer(csvfile)
        data_to_save = [Timestamp, Value,Type]
        c.writerow(data_to_save)
        csvfile.close()

def getCurrentTime():
    current_time = time.time()
    today = datetime.now()
    Timestamp = today.strftime("%Y-%m-%d_%H:%M")
    return Timestamp

def Timeout(current_time, timeout):
    if time.time() > current_time + timeout:
        return False
    else:
        return True
    
def storeData(identity,usage,meterType):
    global PreviousTime
    
    if meterType == str(12) or meterType == str(156) or meterType == str(11):   #gas
        usageDEC=str(usage/100)
    elif meterType == str(13) or meterType == str(203):                         #water
        usageDEC=str(usage/10)
    elif meterType == str(5):                                                   #electricity
        usageDEC=str(usage/100)
    else:
        usageDEC=str(usage)
        print("not of meter type 12, 156, 11, 13, 203, or 5. Decimal point may be incorrect:")
        
    if (getCurrentTime() == PreviousTime and not identity in meterList):    #if .csv does not exist currently
            GPIO.output(greenLED,GPIO.HIGH)
            print(getRoundedTime() + '\tMeterID: #' + identity + ',\tType: ' + meterType + ',\tConsumption: ' + usageDEC + ' m3')
            PreviousTime= getCurrentTime()
            csvLogger(identity,usageDEC,meterType)
            time.sleep(0.1)
            GPIO.output(greenLED,GPIO.LOW)
            meterList.append(identity)
    elif (getCurrentTime() != PreviousTime):                                #if .csv does exist
            meterList.clear()
            GPIO.output(greenLED,GPIO.HIGH)
            print(getRoundedTime() + '\tMeterID: #' + identity + ',\tType: ' + meterType + ',\tConsumption: ' + usageDEC + ' m3')
            PreviousTime= getCurrentTime()
            csvLogger(identity,usageDEC,meterType)
            time.sleep(0.1)
            GPIO.output(greenLED,GPIO.LOW)
            meterList.append(identity)

GPIO.add_event_detect(button, GPIO.RISING, 
        callback=button_pressed_callback, bouncetime=200)

signal.signal(signal.SIGINT, signal_handler)
try:    
    while True:
        GPIO.output(RedLED,GPIO.HIGH)
        time.sleep(1)
        proc = subprocess.Popen('/home/pi/go/bin/rtlamr -msgtype=scm,scm+  -format=json',stdout=subprocess.PIPE, shell=True)
        time.sleep(1)
        number_of_points=0
        current_time = time.time()
        while (1):
            try:
                try:
                    line = proc.stdout.readline()
                except:
                    print("No data!")
                
                try:
                    #print(line)
                    data=json.loads(line.decode("utf-8"))
                    #print(data)
                except ValueError:
                    print("Json error")
                    number_of_points+=1
                    data = False
                    os.execl(sys.executable, sys.executable, *sys.argv)
                
                
                #if (data['EndpointID']):
                try:
                    meterID = str( int(data['Message']['EndpointID']))
                    consumption =  int(data['Message']['Consumption'])
                    metertype = str(data['Message']['EndpointType'])
                    storeData(meterID,consumption,metertype)
                #if (data['ID']):
                except:
                    meterID = str( int(data['Message']['ID']))
                    consumption = int(data['Message']['Consumption'])
                    metertype = str(data['Message']['Type'])
                    storeData(meterID,consumption,metertype)
                       

            except KeyboardInterrupt:
                print("interrupted!")
                val1 = os.system("killall -KILL rtlamr")    
                val2 = os.system("killall -KILL rtl_tcp")
            
        
    exit(0)
except:
    print("crasher I hardley knower!")
    GPIO.setmode(GPIO.BCM)
    GPIO.output(RedLED,GPIO.LOW)
    GPIO.output(greenLED,GPIO.LOW)
    val1 = os.system("killall -KILL rtlamr")    
    val2 = os.system("killall -KILL rtl_tcp")
