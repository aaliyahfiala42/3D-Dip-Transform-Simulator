#   _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ 
#
#   Part II: 3D Dip Reconstructor
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
# python p2_dip_reconstructor.py "path/to/dip_data.csv" 
# python p2_dip_reconstructor.py "dip_data.csv" 

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

def read_csv(value):

    
    path = Path(value)
    if path.suffix.lower() == ".csv" and path.is_file():
        return path

    else:
        raise argparse.ArgumentTypeError( "Enter path to dip data .csv" )

def load_dip_data(path):
    csv = np.loadtxt(path, delimiter=",",skiprows=1)

    dip_ids, counts = np.unique(csv[:, 0], return_counts=True)
    
    k_dips=len(dip_ids) #number of different orientations
    m_slices = counts[0] #number of slices per dip

    #create dip date array
    dips = []
    for dip_id in dip_ids:
        dip = dip_data[dip_data[:, 0] == dip_id]
        dip = dip[np.argsort(dip[:, 3])]
        dips.append(dip)

    dip_data = np.array(dips)

    return dip_data, k_dips, m_slices





parser = argparse.ArgumentParser(description="Dip Reconstructor 9000")


parser.add_argument("path",type=read_csv)
args = parser.parse_args()
dip_data = args.data

dip_data, k_dips, m_slices = load_dip_data(path)

print("____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ ")
print("")
print("Part II:  3D Dipping Reconstructor")
print("____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ ")
print("")
print("        Shape of dip data:  ", dip_data.shape())
print("        # of dips: ", k_dips)
print("        # of slices per dip: ", m_slices)
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
