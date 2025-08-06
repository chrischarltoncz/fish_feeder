# Chris C. 6th AUG 2025

# Rev12 incorporates the camera to grab an image of the feed tube per feeding cycle (4 images per day)
# Rev13 the feed screw was jamming after 50 cycles. Rev13 has new hardware but also turns on the air prior to the feed screw turn
# this should clear fine powdered food from the end of the screw
# calibration went from 20 to 22.5 for 125mg
# Rev14 added 3X gearing to the hopper mech
# this requires V600 speed instead of V200 to account for the gearing
# it also requires reversal of the motor direction because the gear changes it
# Rev16 added function to feed specific tanks for manual use
# Rev19 works 25 tanks
# Rev20 added text file import to define food amounts per tank

import serial
import time
import board
import adafruit_ahtx0
import RPi.GPIO as GPIO
import datetime
from picamera2 import Picamera2

import ast
from typing import Dict, Tuple

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
camera_config = picam2.create_still_configuration(main={"size": (3280, 2464)}, lores={"size": (1920, 1080)}, display="lores")
picam2.configure(camera_config)
picam2.start()

# variable to wait after sending UART command
command_delay = 0.25 # 250milliseconds

# define how much food is dispensed per microstep
# 80 milligrams is 180 degrees on the shaft, at 1/32 stepping is 3200 microsteps
food_scale = 67.5 # microsteps per milligram of food, REV13 is 22.5, REV14 has gearing so 3X = 
#food turns counter
glob_food_tn = 0

# load food amounts, to send to each tank
def load_dual_number_dict(filepath: str) -> Dict[int, Tuple[float, float]]:
    """
    Loads a dictionary from a file with integer keys from 1 to 60,
    each mapping to a 2-number tuple or list.

    Args:
        filepath: Path to the text file.

    Returns:
        Dictionary of int -> (float, float)

    Raises:
        ValueError if the structure is invalid or size is not 60.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    try:
        data = ast.literal_eval(content)
    except Exception as e:
        raise ValueError("File content is not a valid dictionary.") from e

    if not isinstance(data, dict):
        raise ValueError("File does not contain a dictionary.")

    if set(data.keys()) != set(range(1, 61)):
        raise ValueError("Dictionary keys must be integers from 1 to 60.")

    result = {}
    for k, v in data.items():
        if not isinstance(k, int):
            raise ValueError(f"Key {k!r} is not an integer.")
        if not isinstance(v, (tuple, list)) or len(v) != 2:
            raise ValueError(f"Value at key {k} must be a 2-element tuple or list.")
        try:
            result[k] = (float(v[0]), float(v[1]))
        except (TypeError, ValueError):
            raise ValueError(f"Non-numeric values at key {k}: {v}")

    return result

# read the time and date here
def read_time_date():
    x = datetime.datetime.now()
    print(x)
    return (x)

# turn on the food settle vibration motor, vib is time in seconds
def vib_motor(vib):
    ser.write("/1J1R\r".encode()) # motor ON
    time.sleep(vib)
    ser.write("/1J0R\r".encode()) # LIGHT OFF
    time.sleep(command_delay)
    print("Food settled")

# turn ON the vibration or turn it OFF
def mom_vib_motor(state):
    if state:
        ser.write("/1J1R\r".encode()) # motor ON
    if not state:
        ser.write("/1J0R\r".encode()) # motor OFF
 
def save_dat(count, temp, humidity, day_left):
    global glob_food_tn
    file = open("feeder_log_june_2025_rev19.csv","a")
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
    date = read_time_date()
    day = date.day
    name = "hopper_image_date_+" + str(day) + "_" + str(count) + ".jpg"
    print(name)
    time.sleep(0.3)
    picam2.capture_file(f"hopperpics/{name}") # save inside folder 'hopperpics'

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
    ser.write("/2V600L150m80h5j2R\r".encode()) # set the hopper (600 microsteps per second, V600 /3 for gearing),acceleration 500usteps per sec^2 (L500), current 1.9 AMP drive current 0.24amp (m12), hold current 0.1amps (h5), microstepping (1/2  j2)
    time.sleep(command_delay)
    ser.write("/1F1R\r".encode()) # reverse the direction of the rotor motor
    time.sleep(command_delay)
    print("Setup complete")
    time.sleep(3)
    
def home_rotor():
    global index_tank
    print("Home rotor")
    time.sleep(1)
    ser.write("/1Z100000R\r".encode()) # send home command, might not make home
    time.sleep(17)
    index_tank = 0
    
def home_to_port_one(): # from home point, the first port is 1700 microsteps away anticlockwise
    global index_tank
    print("Moving from home to port 1")
    ser.write("/1z10000R\r".encode()) # reset the virtual position, 10000
    time.sleep(command_delay)
    ser.write("/1P1700R\r".encode()) # # 1700 1/32 steps
    time.sleep(2) # 2 second delay
    index_tank = 1
    print("Rotor at Port 1")

def port_anticlock(number): # moves the rotor from port to port, by number many ports
    global index_tank
    print("Moving ", number, " many ports")
    msteps = int(number * 1600) # calc the number of microsteps to move
    command = "/1P" + str(msteps) + "R\r" # command string
    extra_time = (((msteps/3000)*0.1)+0.5) # figure out how long the extra time should be
    how_long = ((msteps/3000)+extra_time) # calculate how long it will take to get there, add in the extra time
    ser.write(command.encode()) # send command to move
    time.sleep(how_long) # wait the calculated time to get there
    index_tank = index_tank + number # increment the tank number
    if index_tank == 31: # if the index_tank has got to 31 its actually back at 1
        index_tank = 1
    print("Rotor at port ",index_tank)

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
    global food_ratio
    food_turn_ok = False # reset the food sent flag to False
    food_ratio = 0 # reset the food check integer
    time_load = 0 # reset the calc for the delay time during loading
    print("Loading food ", quan, "mg")
    ser.write("/2z10000R\r".encode()) # reset the virtual position, 10000
    time.sleep(command_delay) # serial delay
    opto_state = GPIO.input(24) # set opto boolean to True/False based off the opto position on the slot
    steps = int(quan*food_scale) # calc the number of steps based off food scale integer
    command_string = "/2D" + str(steps) + "R\r" # create command string. Rev14 P not D to reverse the motor direction
    ser.write(command_string.encode()) # send the command string
    # calc the delay required based off the amount of food
    time_load = round(((steps/600)+1), 1) # EG 2 turns is 800 microsteps, at 200 microsteps per sec equals 4 seconds. add extra 0.7s. Round to 1dp
    #print("------> calculated time for food loading = ", time_load)
    value = read_thread_loop(time_load, opto_state)
    food_ratio = round((value/(steps/200)), 2) #200 from 99.9
    print("Food ratio (ideally 1) = ", food_ratio)
    
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
    
# new feed function here Rev13
# time_air is how long to blow *prior* to the food loading, which is also during air blow
# quantity is the amount of food in mg
def feed_cycle(time_air, quantity):
    print("Pre-feed air seconds = ", time_air)
    # turn on the air
    ser.write("/2J1R\r".encode()) # SOLENOID ON
    time.sleep(time_air) # wait for time time_air
    # now load the food
    load_food(quantity)
    print("Post-feed air seconds = ", time_air)
    time.sleep(time_air) # wait time_air
    ser.write("/2J0R\r".encode()) # SOLENOID OFF
    print("Feed_cycle complete")
    
def air_clean_rotor(times):
    print("rotating the rotor with the air on to help clean it")
    home_rotor() # home rotor
    time.sleep(2)
    home_to_port_one() # move the rotor from home to port 1
    time.sleep(2)
    ser.write("/2J1R\r".encode()) # SOLENOID ON
    for value in range(times):
        home_rotor() # home rotor
        time.sleep(2)
        home_to_port_one() # move the rotor from home to port 1
        time.sleep(2)
    ser.write("/2J0R\r".encode()) # SOLENOID OFF        

def run_multi_tank_cycle(tank_no):
    global glob_food_tn
    global food_ratio
    global index_tank
    # read food amounts here
    file_path = r"/home/fish/Documents/dual_dict.txt" # file path for food amount here
    dual_dict = load_dual_number_dict(file_path) # put values into dual_dict
    print("------Running the feed cycle------", tank_no, " tanks")
    read_time_date() # read the time and date
    # reset the global food counter
    glob_food_tn = 0
    food_ratio = 1
    # subtract 1 from tank_no
    tank_no -= 1
    # home the rotor
    home_rotor() # home rotor
    # move to port 1
    home_to_port_one() # move the rotor from home to port 1
    # set the variables food_q_list and spare_val. food_q_list is now equal to the food amount
    if index_tank in dual_dict:
        food_q_list, spare_val = dual_dict[index_tank]
    
    # first blow air in port 1 which is the tank port, this is to dry it out
    print("Drying feed tube, 35 seconds")
    blow_air(35, False) # blow air for 45 seconds, NO jiggle so False
    # now load food
    print("Vibrating the hopper to settle the food, 3 seconds")
    vib_motor(3)
    time.sleep(1)
    load_food(food_q_list) # food_q_list quantity of food
    if food_ratio < 0.50:
        print("The hopper screw appears to be jammed, food ratio is below 0.50, halting the test")
        ser.write("/2J0R\r".encode()) # SOLENOID OFF
        stuck = True
        while stuck: # stay here forever
            time.sleep(2)
    time.sleep(2)
    mom_vib_motor(True) # start the motor vibration
    #feed_cycle(4, 125) # 4 seconds, 125mg of food
    blow_air(7, True) # blow the air for 6 seconds to send the food to the tank, with jiggle
    # the tank should now be loaded with food
    mom_vib_motor(False) # stop the motor vibration
    blow_air(3, True) # one more blow air with jiggle
    # adding another blow
    #blow_air(10, True) # one more blow air with jiggle
    # if 1 tank is used function ends here
    # if more tanks to be used for loop here:
    for t in range(tank_no):
        # move the rotor 1 port over
        port_anticlock(1)
        food_ratio = 1
        # first blow air in port 1 which is the tank port, this is to dry it out
        blow_air(35, False) # blow air for 35 seconds, NO jiggle so False
        print("Vibrating the hopper to settle the food, 3 seconds")
        vib_motor(3)
        time.sleep(1)
        # now load food, start by reading the food value:
        # set the variables food_q_list and spare_val. food_q_list is now equal to the food amount
        if index_tank in dual_dict:
            food_q_list, spare_val = dual_dict[index_tank]
        load_food(food_q_list) # 60 milligrams of food. NEW SCREW SO MORE
        if food_ratio < 0.50:
            print("The hopper screw appears to be jammed, food ratio is below 0.50, halting the test")
            ser.write("/2J0R\r".encode()) # SOLENOID OFF
            stuck = True
            while stuck: # stay here forever
                time.sleep(2)
        time.sleep(2)
        #feed_cycle(4, 125) # 4 seconds, 125mg of food
        mom_vib_motor(True) # start the motor vibration
        blow_air(7, True) # blow the air for 10 seconds to send the food to the tank, with jiggle
        # the tank should now be loaded with food
        mom_vib_motor(False) # stop the motor vibration
        blow_air(3, True) # one more blow air with jiggle
    air_clean_rotor(3) # clean the rotor/stator
    print("--Feed cycle complete--")
      
def main_time_loop_run(tanks):    
    setup_fish()
    time.sleep(4)
    home_rotor()
    time.sleep(5)
    home_to_port_one() # move the rotor from home to port 1
    time.sleep(5)
    days_left = True # used to control number of days to keep running
    days_running = 30 # 30 days to run
    max_cycles = 120 # when 120 cycles have run the system stops
    cycle_counter = 0
    dry_counter = 0
    rot_posn = 1
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
                print("dry counter = ", dry_counter)
                time.sleep(10) # wait 10 seconds
                dry_counter += 1 # inc counter
                if dry_counter == 120: # 20 minutes
                    dry_counter = 0
                    port_anticlock(1)
                    time.sleep(2)
                    rot_posn += 1 # increment rotor position
                    if rot_posn >= tanks+1:
                        rot_posn = 1
                        home_rotor()
                        time.sleep(5)
                        port_anticlock(1)
                        time.sleep(10)        
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
                print("------30 days elapsed, feeder halted------")
            print("----FOOD CYCLE RUNNING NOW----", (max_cycles-cycle_counter), "cycles left")
            run_multi_tank_cycle(tanks) # run the feed cycle function at the 6 hour mark
    except KeyboardInterrupt:
        pass


# Main script here:

# MAIN RUN PROGRAM HERE:
print("Starting multi tank script, 6 hour feed cycles")
#main_time_loop_run(25) # 25 tanks to feed
# MAIN PROG END

setup_fish()
time.sleep(2)
run_multi_tank_cycle(25)





































  
#air_clean_rotor(2)

#vib_motor(0.4)
#setup_fish()
#time.sleep(2)
#run_multi_tank_cycle(25)
#ser.write("/2J1R\r".encode()) # SOLENOID ON
#time.sleep(2)
#home_rotor()
#time.sleep(2)
#home_to_port_one() # move the rotor from home to port 1
#load_food(30)
#ser.write("/2J0R\r".encode()) # SOLENOID OFF
#blow_air(2, False)
#time.sleep(35)
#blow_air(15, False) # 
#home_rotor()
#time.sleep(2)
#home_to_port_one() # move the rotor from home to port 1
#ser.write("/2J0R\r".encode()) # SOLENOID OFF
#home_to_port_one() # move the rotor from home to port 1
#port_anticlock(1)
#blow_air(15, False)
#print("Feed in 5 seconds")
#time.sleep(5)
#blow_air(5, False) # blow air for 60 seconds, NO jiggle so False
#feed_cycle(3, 125) # 4 seconds, 125mg of food
#blow_air(3, True)
#vib_motor(2)
#time.sleep(4)
#vib_motor(False)
#run_multi_tank_cycle(10)
#cam_light(True) # LED light ON
#grab_cam_frame(9999)
# .jpg saved
#cam_light(False) # LED light OFF
#home_rotor() # home rotor
#time.sleep(6)
# move to port 1
#home_to_port_one() # move the rotor from home to port 1
#for x in range(9):
#blow_air(5, False) # blow air for 60 seconds, NO jiggle so False
#time.sleep(3)
#feed_cycle(4, 125) # 4 seconds, 125mg of food
#blow_air(2, True) # blow the air for 10 seconds to send the food to the tank, with jiggle
#time.sleep(3)
#blow_air(10, True) # blow the air for 10 seconds to send the food to the tank, with jiggle
#time.sleep(3)
#blow_air(10, True) # blow the air for 10 seconds to send the food to the tank, with jiggle
