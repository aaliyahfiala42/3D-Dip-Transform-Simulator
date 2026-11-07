#   _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ 
#
#   Virtual Dip Simulator
#   _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ 
# 
#   This script simulates dipping a 3D object into water and taking regular measurments of water depth, at various orientations (phi, theta) of the object.
#   The dip_data.csv output can then be used in the neighboring dip reconstruction script to reconstruct the object as a mesh .obj
#   This idea is accredited to the authors of "Dip Transform for 3D Shape Reconstruction", and is a reconstruction of their work, with minor modifications.
#  
#   The core concept is based on the Archimedean Principle, that the volume of the water displaced is equivalent to the volume displaced.
#   
#   Author: Aaliyah Hänni
#   Date: 17.12.2026
#
#   _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ 

#TODO: need to add to a requirements.txt
import argparse
from pathlib import Path

import trimesh
import numpy as np
import scipy


#loading animation
import itertools
import threading
import time
from contextlib import contextmanager

#   _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ 

#USER INPUTS
# 1. default shape (select from: "sphere", "cube", "icosahedron") selection OR path to .obj
# 2. number of dips (integer range 0-10000)
# 3. noise level (integer range 0-100), default none = 0  (coming soon)


#OUTPUTS
# csv
# columns = ["dip no.", "theta", "phi", "water_height_measurement_mm", "displace_vol_mm3"]
 

# Run cmd example:
# python dip_simulator.py sphere/cube/icosahedron || "path/to/.obj" number_of_dips noise_level
# python dip_simulator.py sphere 10 0

#   _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ 

# PARSE USER INPUT

def shape_or_obj(value):
    if value in ("sphere", "cube", "icosahedron"):
        return value
    
    mesh = Path(value)
    if mesh.suffix.lower() == ".obj" and mesh.is_file():
        return mesh

    raise argparse.ArgumentTypeError( "Enter default shape (sphere, cube, icosahedron) OR path to .obj" )


def integer_range(minimum, maximum):
    def validate(value):
        try:
            number = int(value)
        except:
            raise argparse.ArgumentTypeError("Input not an integer.")
        
        if not minimum <= number <= maximum:
            raise argparse.ArgumentTypeError("Input outside allowed range.")
        return number
    return validate


parser = argparse.ArgumentParser(description="3D Dipping Simulator")

parser.add_argument("shape",type=shape_or_obj)
parser.add_argument("dips",type=integer_range(0, 100000))
parser.add_argument("noise",type=integer_range(0, 100))
args = parser.parse_args()


print("____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ ")
print("")
print("Welcome to the 3D Dipping Simulator!")
print("____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ ")
print("")
print("     You have selected the following options: ", )
print("        Shape: ", args.shape)
print("        # of dips: ", args.dips)
print("        Noise level: ", args.noise)
print("____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ ")
print("")



@contextmanager
def loading(message="*water sloshing noising*"):
    stop = threading.Event()

    def animate():
        for frame in itertools.cycle("|/-\\"):
            if stop.is_set():
                break
            print(f"\r{message} {frame}", end="", flush=True)
            stop.wait(0.1)

    thread = threading.Thread(target=animate, daemon=True)
    thread.start()

    try:
        yield
    finally:
        stop.set()
        thread.join()
        print("\r" + " " * (len(message) + 2) + "\r", end="", flush=True)



with loading("Simulating dips"):
    time.sleep(5)


print("\nDry off your object and check out the dip_data.csv.\n")
#   _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ 
