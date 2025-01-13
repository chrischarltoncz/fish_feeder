# Chris C. 1st Nov 2024
# Basic fish feeder script for initial single tank test
# Assumption is 20 fish in the tank
# 25mg of food per fish per day, so 500mg of food per day
# 4 feedings per day, so 125mg per feeding
# Rev3 basic version, should work but needs bugs checked - have to fix days variable that doesn't work currently
# Rev4 checked for bugs, checked functions are up to date

import serial
import time
import board
import adafruit_ahtx0
import RPi.GPIO as GPIO
import datetime
from picamera2 import Picamera2

# GPIO
GPIO.setup(24, GPIO.IN) # this is the hopper opto thread sensor input

# UART port definition 
port = "/dev/ttyAMA0"
baud = 9600
# UART port:
ser = serial.Serial("/dev/serial0", baudrate=9600, timeout=2.0)
    # open the serial port
if ser.isOpen():
    print(ser.name + ' is open...')

# Temp/Hum sensor AHT
sensor = adafruit_ahtx0.AHTx0(board.I2C())

# camera here
picam2 = Picamera2()
camera_config = picam2.create_still_configuration(main={"size": (1920, 1080)}, lores={"size": (640, 480)}, display="lores")
picam2.configure(camera_config)
picam2.start()

# variable to wait after sending UART command
command_delay = 0.25 # 250milliseconds

# define how much food is dispensed per microstep
# 80 milligrams is 180 degrees on the shaft, at 1/32 stepping is 3200 microsteps
food_scale = 20.0 # microsteps per milligram of food, REV8 is 20, REV7 was 17.5
#food turns counter
glob_food_tn = 0 

# read the time and date here
def read_time_date():
    x = datetime.datetime.now()
    print(x)
    return (x)

def save_dat(count, temp, humidity, day_left):
    global glob_food_tn
    file = open("feeder_log.csv","a")
    t = str(temp)
    h = str(humidity)
    c = str(count)
    d = str(day_left)
    CTD = str(read_time_date())
    GFC = str(glob_food_tn)
    file.write(c + "," + t + "," + h + "," + d + "," + CTD + "," + GFC + "\n")
def save_heading():
    file = open("feeder_log.csv","a")
    file.write("Count" + "," + "Temp" + "," + "Humid" + "," + "Day left" + "," + "date_time" + "," + "food_count" + "\n")
    
# read and return the temperature and humidity
def read_temp_hum():
    hum = 0
    temp = 0
    print("Reading the temperature and humidity")
    print("\nTemperature: %0.1f C" % sensor.temperature)
    print("Humidity: %0.1f %%" % sensor.relative_humidity)
    print(" ")
    hum = round(sensor.relative_humidity, 2)
    tem = round(sensor.temperature, 1)
    return (tem, hum)

def grab_cam_frame(count):
    name = "hopper" + str(count) + ".jpg"
    print(name)
    time.sleep(0.3)
    picam2.capture_file(name)

# time_long is number of second to delay, 0.02 second increments are acceptable
# state is a boolean of the state of the opto read *prior* to issuing a motor rotate command
# if the state is True then it means the opto was resting on a slot before moving occured and so an extra +1 is added
def read_thread_loop(time_long, state):
    print("Reading the thread opto in a loop")
    global glob_food_tn
    tot_count = 0 # reset the counter
    escape = 0 # reset escape
    delay_loop_time = 0.02
    #times_to_loop = 50 #time_long/0.1 # EG 35 loops is 3.5/0.1
    times_to_loop = int(time_long/delay_loop_time) # EG 175 loops is 3.5 seconds/0.02 
    for x in range(times_to_loop): # loop this around time_long times
        if GPIO.input(24): # if the pin goes True
            #print("opto HIGH")
            wait_for_false = True
            tot_count += 1 # increment the counter
            while wait_for_false and escape < 50: # stay inside this loop until wait_for_false = False
                time.sleep(delay_loop_time) #delay
                wait_for_false = GPIO.input(24) # update flag
                #print(wait_for_false)
                escape += 1 # increment escape
        time.sleep(delay_loop_time) #delay
    if state: # if state is True, add 1 to the counter
        tot_count += 1 # add 1
    glob_food_tn += tot_count # add the tot_count value to global counter
    return(tot_count)

def setup_fish():
    # setup here:
    print("Running setup")
    ser.write("/1TR\r".encode()) # reset #1
    time.sleep(command_delay)
    ser.write("/2TR\r".encode()) # reset #2
    time.sleep(command_delay)
    ser.write("/1V3000L200m80h20j32R\r".encode()) # set the rotor speed (3000 microsteps per second, V3000),acceleration 200usteps per sec^2 (L200), drive current 1amp (m80), hold current 0.4amps (h20), microstepping (1/32  j32)
    time.sleep(command_delay)
    ser.write("/2V200L500m75h5j2R\r".encode()) # set the hopper (200 microsteps per second, V200),acceleration 500usteps per sec^2 (L500), current 1.9 AMP drive current 0.24amp (m12), hold current 0.1amps (h5), microstepping (1/2  j2)
    time.sleep(command_delay)
    ser.write("/1F1R\r".encode()) # reverse the direction of the rotor motor
    time.sleep(command_delay)
    print("Setup complete")
    time.sleep(3)
    
def home_rotor():
    print("Home rotor")
    time.sleep(1)
    ser.write("/1Z100000R\r".encode()) # send home command, might not make home
    time.sleep(17)
    
def home_to_port_one(): # from home point, the first port is 1700 microsteps away anticlockwise
    print("Moving from home to port 1")
    ser.write("/1z10000R\r".encode()) # reset the virtual position, 10000
    time.sleep(command_delay)
    ser.write("/1P1700R\r".encode()) # # 1700 1/32 steps
    time.sleep(2) # 2 second delay
    print("Rotor at Port 1")

def port_anticlock(number): # moves the rotor from port to port, by number many ports
    print("Moving ", number, " many ports")
    msteps = int(number * 1600) # calc the number of microsteps to move
    command = "/1P" + str(msteps) + "R\r" # command string
    extra_time = (((msteps/3000)*0.1)+0.5) # figure out how long the extra time should be
    how_long = ((msteps/3000)+extra_time) # calculate how long it will take to get there, add in the extra time
    ser.write(command.encode()) # send command to move
    time.sleep(how_long) # wait the calculated time to get there

def jiggle_rotor():
    for x in range(2):
        # move backwards 12 steps
        ser.write("/1D200R\r".encode())
        time.sleep(0.35)
        # move forwards 12 steps
        ser.write("/1P200R\r".encode())
        time.sleep(0.35)

def blow_air(long, simple): # long is the blow time in seconds, simple is a boolean to enable jiggle or not
    print("Blowing Hopper air")
    if simple:
        for x in range(3):       
            ser.write("/2J1R\r".encode()) # SOLENOID ON
            time.sleep(0.3)
            ser.write("/2J0R\r".encode()) # SOLENOID OFF
            time.sleep(1.1)
            jiggle_rotor()
            time.sleep(1.1)
    ser.write("/2J1R\r".encode()) # SOLENOID ON
    time.sleep(long) # leave the solenoid on for this time (long)
    ser.write("/2J0R\r".encode()) # SOLENOID OFF
    time.sleep(0.5)
    print("Finished blowing air")

def load_food(quan):
    food_turn_ok = False # reset the food sent flag to False
    food_ratio = 0 # reset the food check integer
    time_load = 0 # reset the calc for the delay time during loading
    print("Loading food ", quan, "mg")
    ser.write("/2z10000R\r".encode()) # reset the virtual position, 10000
    time.sleep(command_delay) # serial delay
    opto_state = GPIO.input(24) # set opto boolean to True/False based off the opto position on the slot
    steps = int(quan*food_scale) # calc the number of steps based off food scale integer
    command_string = "/2D" + str(steps) + "R\r" # create command string
    ser.write(command_string.encode()) # send the command string
    # calc the delay required based off the amount of food
    time_load = round(((steps/200)+1), 1) # EG 2 turns is 800 microsteps, at 200 microsteps per sec equals 4 seconds. add extra 0.7s. Round to 1dp
    #print("------> calculated time for food loading = ", time_load)
    value = read_thread_loop(time_load, opto_state)
    food_ratio = round((value/(steps/66.66)), 2)
    print("Food loading ratio, should be 1 = ", food_turn_ok)
    
# empty the hopper out, how_long defines how many seconds to run
def empty_hopper(how_long):
    loops = round((how_long)/44.5)
    print(" Empty the hopper to port 1 ", how_long, " seconds")
    # home the rotor
    home_rotor() # home rotor
    # move to port 1
    home_to_port_one() # move the rotor from home to port 1
    # now loop, loading a large amount of food each time then blowing it
    for value in range(loops):
        # now load food
        load_food(500) # 500 milligrams of food
        blow_air(10, True) # blow the air for 10 seconds to send the food to the tank, with jiggle
    print(" Empty hopper complete")

# new send food function. Turns on the air *first* then loads food in to the tube
# flush time is the time to run the air prior to the start of the food load
def send_food(flush_time, food_quant):
    ser.write("/2J1R\r".encode()) # SOLENOID ON, start the air flush
    time.sleep(flush_time) # wait this long before starting the food load
    # now load the food while the air is running
    load_food(food_quant)
    time.sleep(1.5) # add 1.5 second of delay after loading the food
    ser.write("/2J0R\r".encode()) # SOLENOID OFF
    print("Send food complete")

def run_multi_tank_cycle(tank_no):
    global glob_food_tn
    print("------Running the feed cycle------", tank_no, " tanks")
    read_time_date() # read the time and date
    # reset the global food counter
    glob_food_tn = 0
    # subtract 1 from tank_no
    tank_no -= 1
    # home the rotor
    home_rotor() # home rotor
    # move to port 1
    home_to_port_one() # move the rotor from home to port 1
    # first blow air in port 1 which is the tank port, this is to dry it out
    blow_air(75, False) # blow air for 60 seconds, NO jiggle so False
    # now load food
    #load_food(125) # 125 milligrams of food
    send_food(3, 125) # send food, 4 second air blow before thread turn and load
    blow_air(15, True) # blow the air for 10 seconds to send the food to the tank, with jiggle
    # the tank should now be loaded with food
    blow_air(3, True) # one more blow air with jiggle
    # adding another blow
    blow_air(10, True) # one more blow air with jiggle
    # if 1 tank is used function ends here
    # if more tanks to be used for loop here:
    for t in range(tank_no):
        # move the rotor 1 port over
        port_anticlock(1)
        # first blow air in port 1 which is the tank port, this is to dry it out
        blow_air(60, False) # blow air for 60 seconds, NO jiggle so False
        # now load food
        #load_food(125) # 125 milligrams of food
        send_food(3, 125) # send food, 4 second air blow before thread turn and load
        blow_air(10, True) # blow the air for 10 seconds to send the food to the tank, with jiggle
        # the tank should now be loaded with food
        blow_air(3, True) # one more blow air with jiggle 
    print("--Feed cycle complete--")
      
def main_time_loop_run(tanks):
    setup_fish()
    days_left = True # used to control number of days to keep running
    days_running = 20 # 20 days to run
    max_cycles = 80 # when 80 cycles have run the system stops
    cycle_counter = 0
    save_heading() # save data log heading
    try:
        while days_left == True:
            for x in range(2160):
                hours = ((2160-x)/360)
                hours_int = int(hours)
                mins_int = int((hours-hours_int)*60)
                print(hours_int, " hours", mins_int, " minutes until the next feed cycle. Ctrl&c to HALT")
                day_remain = int(((max_cycles-cycle_counter)/4))
                print("Days left to run = ", day_remain)
                time.sleep(10) # wait 10 seconds
            cycle_counter += 1 # increment the cycle counter
            # log data
            temp, humidity = read_temp_hum()
            save_dat(cycle_counter, temp, humidity, day_remain)
            # data logged
            # save image
            grab_cam_frame(cycle_counter)
            # .jpg saved
            if cycle_counter == max_cycles:
                days_left = False
                print("------20 days elapsed, feeder halted------")
            print("----FOOD CYCLE RUNNING NOW----", (max_cycles-cycle_counter), "cycles left")
            run_multi_tank_cycle(tanks) # run the feed cycle function at the 6 hour mark
    except KeyboardInterrupt:
        pass

# clean rotor function. Over time fine food gets between the rotor and stator, this function helps clear it out, it is blown out of the spare holes
# and the edge of the rotor
def clean_rotor(times):
    print("Running rotor clean")
    # home the rotor first:
    home_rotor()
    # homed
    # go to port 1
    home_to_port_one()
    # now at port 1
    time.sleep(command_delay)
    ser.write("/1TR\r".encode()) # reset #1, the rotor motor controller
    time.sleep(command_delay)
    # change the rotor motor drive parameters
    ser.write("/1V1000L200m80h20j32R\r".encode()) # set the rotor speed (1000 microsteps per second, V1000),acceleration 200usteps per sec^2 (L200), drive current 1amp (m80), hold current 0.4amps (h20), microstepping (1/32  j32)
    time.sleep(command_delay)
    # switch on the air supply
    ser.write("/2J1R\r".encode()) # SOLENOID ON
    time.sleep(command_delay)
    # rotate the rotor the number of times in (times)
    for x in range(times):
        # rotate the rotor 360 degrees:
        ser.write("/1z10000R\r".encode()) # reset the virtual position, 10000
        time.sleep(command_delay)
        ser.write("/1P48000R\r".encode()) # # 48000 1/32 steps
        time.sleep(55) # 55 second delay to fully rotate
    # change the rotor parameters back to stock again at the end
    time.sleep(command_delay)
    # turn off the solenoid:
    ser.write("/2J0R\r".encode()) # SOLENOID OFF
    time.sleep(command_delay)
    # reset the rotor controller parameters back
    ser.write("/1V3000L200m80h20j32R\r".encode()) # set the rotor speed (3000 microsteps per second, V3000),acceleration 200usteps per sec^2 (L200), drive current 1amp (m80), hold current 0.4amps (h20), microstepping (1/32  j32)
    time.sleep(command_delay)
# rotor clean end    

# basic description of the operations for this script:

# reads in the time and date, will do more with this later
# there are 4 feedings per 24 period, so once every 6 hours, total per 24 hours is 500mg of food
# when the script is started it starts counting the first 6 hours
# 
# 



# Main script here:

# MAIN RUN PROGRAM HERE:
print("Starting multi tank script, 6 hour feed cycles")
main_time_loop_run(3) # 3 tanks to feed
# MAIN PROG END



#setup_fish()
#time.sleep(1)

#run_multi_tank_cycle(3)

#home_rotor() # home rotor
# move to port 1
#home_to_port_one() # move the rotor from home to port 1
#for x in range(9):
#load_food(125) # 125 milligrams of food
    #time.sleep(3)
#blow_air(10, True) # blow the air for 10 seconds to send the food to the tank, with jiggle
#time.sleep(3)
#blow_air(10, True) # blow the air for 10 seconds to send the food to the tank, with jiggle
#time.sleep(3)
#blow_air(10, True) # blow the air for 10 seconds to send the food to the tank, with jiggle
