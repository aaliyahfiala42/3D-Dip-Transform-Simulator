#   _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ 
#
#   Part I: Virtual Dip Simulator
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

#USER INPUTS
# 1. default shape (select from: "sphere", "cube", "icosahedron") selection OR path to .obj
# 2. number of dips (integer range 0-10000)
# 3. noise level (integer range 0-100), default none = 0  (#TODO coming soon)


#OUTPUTS
# csv
# columns = ["dip no.", "theta", "phi", "water_height_measurement_mm", "displace_vol_mm3"]
 

#Assumptions:
# mesh is watertight and centered at the origin
# size of the mesh correlates to how detailed it is 


# Run cmd example:
# python p1_dip_simulator.py sphere/cube/icosahedron || "path/to/.obj" number_of_dips noise_level
# python p1_dip_simulator.py sphere 10 0
# python p1_dip_simulator.py "./meshes/pisa.obj" 10 0


#   _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ 


# TODO: need to add to a requirements.txt, remove packages no longer used
import argparse
from pathlib import Path

import trimesh
import numpy as np
import scipy


import itertools
import threading
import time
from contextlib import contextmanager


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
parser.add_argument("dips",type=integer_range(1, 100000))
parser.add_argument("noise",type=integer_range(0, 100))
args = parser.parse_args()
shape = args.shape
number_of_dips = args.dips
noise_level = args.noise


print("____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ ")
print("")
print("Part I: 3D Dipping Simulator")
print("____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ ")
print("")
print("        Shape: ", shape)
print("        # of dips: ", number_of_dips)
print("        Noise level: ", noise_level)
print("____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ ")
print("")


@contextmanager
def loading(message="Dip simulation in process: "):
    stop = threading.Event()

    def animate():
        frames = [
            "﹏﹏﹏﹏⛴﹏﹏",
            "﹏﹏﹏⛴﹏﹏﹏",
            "﹏﹏⛴﹏﹏﹏﹏",
            "﹏⛴﹏﹏﹏﹏﹏",
            "﹏﹏⛴﹏﹏﹏﹏",
            "﹏﹏﹏⛴﹏﹏﹏",
            "﹏﹏﹏﹏⛴﹏﹏",
            "﹏﹏﹏﹏﹏⛴﹏",
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
    #time.sleep(5)


    #   _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ 
    #FUNCTION DEFINTIONS

    ############################################################################
    # Purpose: convert the shape into a triangle mesh 
    # Inputs: shape STRING (either a default selction or .obj)
    # Outputs: trimesh triangle mesh 
    ############################################################################    
    
    def get_mesh(shape, verbose=0):
    
        if shape == "sphere":
            mesh = trimesh.creation.icosphere( subdivisions=3, radius=20)
        elif shape == "cube":
            mesh = trimesh.creation.box(extents=[10,10,10])
        elif shape == "icosahedron":
            mesh = trimesh.creation.icosphere(subdivisions=0, radius=20)
        else:
            mesh = trimesh.load(shape, force="mesh")
        
        if verbose: 
            print("")
            print("1. Input Mesh: ")
            print("     vertices: ", len(mesh.vertices))
            print("     faces: ", len(mesh.faces))
            print("     volume: ", mesh.volume)
            print("     surface area: ", mesh.area)
            print("     bounds: ", mesh.bounds)
            print("     watertight   : ", mesh.is_watertight)
            print("")

                    
        return mesh

    ############################################################################
    # Purpose:
    # Inputs:
    # Outputs: 
    ############################################################################    
    
    def apply_voxelization(mesh, target_grid_width = 100, verbose=0):

        #est mesh longest side, number of voxels needed to fill it
        mesh_size = mesh.extents.max()
        pitch = mesh_size / target_grid_width

        #voxelize it 
        voxel_grid = mesh.voxelized(pitch=pitch).fill()
        voxels = voxel_grid.matrix

        if verbose:
            print("")
            print("Voxelization: ")
            print("     voxel pitch size: ", pitch)
            print("     voxel grid: ", voxels.shape)
            print("     error est. (% actual vs voxel volume) : ", (abs(mesh.volume - voxel_grid.volume) / mesh.volume) * 100 )
            print("")

        return voxel_grid, pitch


    def generate_orientations(number_of_dips, verbose=0):
        indices = np.arange(number_of_dips)
        
        # Approximately uniform distribution on a sphere
        z = 1 - 2 * (indices + 0.5) / number_of_dips
        golden_angle = np.pi * (3 - np.sqrt(5)) #from wolfram mathworld
        phi = indices * golden_angle
        theta = np.arccos(z)

        # Convert to degrees
        theta = np.degrees(theta)
        phi = np.degrees(phi) % 360

        orientations = np.column_stack((theta, phi))

        if verbose:
            print("")
            print("3. Orientations: ")
            print("     # of orientations:", orientations.shape)
            print("")

        return orientations

    #Helper function: calculate normal direction from orientations phi,theta (deg)
    def get_normal(theta, phi):
        theta=np.radians(theta) #conver to radians
        phi=np.radians(phi)

        #calculate vector
        nx=np.sin(theta) * np.cos(phi)
        ny=np.sin(theta)*np.sin(phi)
        nz=np.cos(theta)
        return np.array([nx, ny, nz])


    def dip_simulator(mesh_voxelized, orientations, pitch, m_slices = 100, verbose = 0):
        #m: # of uniform measurements taken in a single dip

        dips=[]
        grid_coords = mesh_voxelized.points #occupied voxel positions
        
        for i, (theta, phi) in enumerate(orientations):
            n = get_normal(theta, phi)
            d = grid_coords @ n #project the voxel center positions, normal to the water surface

            #divide the take into m uniform slices 
            water_h = np.linspace(d.min() - pitch, d.max() + pitch, m_slices)

            #count the number voxels submerged at each water height m_i
            counts = np.array([np.count_nonzero(d <= h) for h in water_h])
            vol_h = counts * pitch**3

            dip = np.column_stack([
                np.full(m_slices, i+1),
                np.full(m_slices, theta),
                np.full(m_slices, phi),
                water_h,
                vol_h
            ])
            dips.append(dip)

        dip_data = np.array(dips)
        if verbose:
            print("")
            print("Dipped object: ")
            print("     Dip Data shape: ", dip_data.shape)
            print("")

        return dip_data
 
    def create_csv(dip_data):
    
        dip_output = dip_data.reshape(-1,5) #flatten to 2D

        columns = ["dip no.", "theta", "phi", "water_height_measurement_mm", "displace_vol_mm3"]

        np.savetxt("dip_data.csv", dip_output, delimiter=",", header=",".join(columns), comments="", fmt="%.4f" )
 
 
    #   _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ 
 
 
    #Run the simulation in steps


    #1. Load user input as a mesh we can work with
    mesh = get_mesh(shape,  verbose=0)

    #2. Voxelize the mesh 
    mesh_voxelized, pitch = apply_voxelization(mesh, verbose=0)

    #3. Generate orientations from the number of dips, using Fibonacci Sphere
    orientations = generate_orientations(number_of_dips)

    #4. Apply dips, startup the machine, build the dip data matrix
    dip_data = dip_simulator(mesh_voxelized, orientations, pitch, m_slices = 100, verbose=0)

    #create the csv output
    create_csv(dip_data)


print("\nDry off your mesh and check out dip_data.csv.\n")



