# fish_feeder

![image](https://github.com/user-attachments/assets/decc2745-dc93-4acf-bb86-ad038419c31a)

This is the python code to run the pneumatic fish feeder system which functions as follows:

The food is placed in a clear plastic cylinder/hopper. There is an illumination LED strip to light it up on one side. A Pi camera on the opposite side to capture images of the tube and the food. This image will be used for tracking food consumption and level.

The base of the tube has the main feeder body, this incorporates a delrin screw drive to move the food. The screw is rotated via at NEMA17 motor at one end, at the opposite end is an opto sensor and a 6 slot chopper for counting the rotations. This is used to confirm the rotation happens and the motor is not jammed.

The thread deposits the food into a conical volume, this funnels it down to a fitting where it exits the food hopper body/assembly. Above the conical volume is mounted an air solenoid valve, it is fed via 22-25psi house air. The air supply is split off via a needle valve to supply a small continuous stream of air that travels to the bulk food.
This is to keep it dry, it also passes over a temperature and humidity sensor to record the values, this ensures the food is always exposed to dry air and if there is an air supply problem it can be flagged.

Currently (Jan 2025) the air solenoid is turned on prior to the food loading screw rotation, this is to equalize the pressure along the various parts (thread/hopper) so fine powdered food does not flow and collect/jam the screw mech.

Once the food passes out of the food hopper mech, it passes to the rotary valve mechanism.

There is a curved interface tube which is centrally located and passes to near the circumference of a rotating disc, this disc has embedded magnets which lightly clamp the rotor to the stator, the stator underneath has 30X fittings which correspond to each fish tank. 

The rotor is turned via a belt which is in turn rotated via a NEMA23 stepper motor. A home sensor microswitch is stationary on the main feeder assembly, it activates via a 3D printed bump which is VHB taped to the rotor. There is a well defined number of microsteps between home and port 1 so the system can home and index to the correct port location.

One each feeding cycle the rotor is re-homed, then indexed to port 1. Prior to food loading the tank/port is air dried for a number of seconds (typically 60-75) to dry the end of the tube to avoid wet food. 

Links:

Stepper motor drive boards:
https://www.allmotion.com/ezhr17en

Onshape design:
[https://www.allmotion.com/ezhr17en
](https://cad.onshape.com/documents/b092e7b6adc17bd3a3390fe1/w/5d2cf434299dfa3fc55c8225/e/223d4cf3e3f1612e807b6f1d?renderMode=0&uiState=6785ac46c4b3921eef4992e4)
