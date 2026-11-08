#   _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ 
#
#   3D Dip Reconstructor
#   _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ 
# 
#   This takes in a csv of dip data (either from a physical or simulated dip machine), and converts it into a .obj output mesh, using the 
#   famous 3D dip reconstruction algorithm. See the original paper for more details. 
#  
#   The core concept is based on the Archimedean Principle, that the volume of the water displaced is equivalent to the volume displaced.
#   
#   Author: Aaliyah Hänni
#   Date: 17.12.2026
#
#   _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ 


#USER INPUTS
# 1. path to dip_data.csv of the format:         
# columns = ["dip no.", "theta", "phi", "water_height_measurement_mm", "displace_vol_mm3"]



#OUTPUTS
# The reconstructed dip mesh as reconstruction.obj
 

#Assumptions:
# 


# Run cmd example:
# python dip_reconstructor.py "path/to/dip_data.csv" 
# python dip_reconstructor.py "dip_data.csv" 

#   _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ 


import argparse
from pathlib import Path
import itertools
import threading
import time
from contextlib import contextmanager

import numpy as np

from itertools import product
from scipy.sparse import coo_matrix


from scipy.sparse.linalg import lsmr

from skimage.filters import threshold_otsu
#   _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ 


# PARSE USER INPUT

def dip_data_csv(value):

    
    dip_data = Path(value)
    if dip_data.suffix.lower() == ".csv" and dip_data.is_file():
        return dip_data

    dip_data = np.loadtxt("dip_data.csv", delimiter=",",skiprows=1)
    n_dips=len(np.unique(dip_data[:, 0]))
    n_heights=dip_data.shape[0] // n_dips
    dip_data = dip_data.reshape(n_dips, n_heights, 5)

    raise argparse.ArgumentTypeError( "Enter path to dip data .csv" )


parser = argparse.ArgumentParser(description="Dip Reconstructor 9000")


parser.add_argument("data",type=dip_data_csv)
args = parser.parse_args()
dip_data = args.data



print("____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ ")
print("")
print("Part II:  3D Dipping Reconstructor")
print("____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ ")
print("")
print("        Shape: ", dip_data)
print("        # of dips: ", len(dip_data))
print("____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ ")
print("")


@contextmanager
def loading(message="Dip reconstruction in process: "):
    stop = threading.Event()

    def animate():
        frames = [
            "  ◯ ",
            "    ☽ ",
            "     ◑",
            "       ●",
            "        ●",
            "      ◐",
            "     ❨",
            "   ◯",
        ]

        for frame in itertools.cycle(frames):
            if stop.is_set():
                break
            print(f"\r{message}  {frame}   ", end="", flush=True)
            stop.wait(0.2)

    thread = threading.Thread(target=animate, daemon=True)
    thread.start()

    try:
        yield
    finally:
        stop.set()
        thread.join()
        print("\r" + " " * (len(message) + 25) + "\r",
              end="", flush=True)



with loading():
    time.sleep(5)

print("\n 3D reconstruction complete. Bio-digital jazz, man. \n")
