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
# 2. TODO: optional select solver type (SVD, Cholesky, LSMR, LSQR) 
#       default: LSMR
# 3. TODO: option thresholding level (default is Otsu's method)


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
import trimesh

from itertools import product
from scipy.sparse import coo_matrix
from scipy.interpolate import PchipInterpolator
from scipy.optimize import lsq_linear
from scipy.sparse import csr_matrix, eye, vstack
from scipy.ndimage import gaussian_filter

from scipy.sparse.linalg import lsmr
from scipy.sparse import kron, eye, csr_matrix, block_diag


from skimage.filters import threshold_otsu
from skimage.measure import marching_cubes

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
        dip = csv[csv[:, 0] == dip_id]
        dip = dip[np.argsort(dip[:, 3])]
        dips.append(dip)

    dip_data = np.array(dips)

    return dip_data, k_dips, m_slices





parser = argparse.ArgumentParser(description="3D Dip Reconstructor")
parser.add_argument("path",type=read_csv)
args = parser.parse_args()
path = args.path
dip_data, k_dips, m_slices = load_dip_data(path)

print("____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ ")
print("")
print("Part II:  3D Dipping Reconstructor")
print("____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ ")
print("")
print("        Shape of dip data:  ", dip_data.shape)
print("        # of dips: ", k_dips)
print("        # of slices per dip: ", m_slices)
print("____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ ")
print("")


@contextmanager
def loading(message="Dip reconstruction in process: "):
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


    #n: # voxels along one axis
    #N: # voxels in the entire cubic grid
    #extent: length of one axis (mm)
    #pitch: length of one cubic voxel (mm)
    #padding: 

    def define_gridspace(dip_data, n=100, padding=1.1, verbose=0):
        N = n**3
        max_height = np.max(np.abs(dip_data[:,:,3])) #find the max water height in the dataset 
        extent = (2 * max_height * padding)
        pitch = extent / n
        if verbose:
            print("")
            print("Grid Stats: ")
            print("     # voxels along one axis: ", n)
            print("     # voxels total: ", N)
            print("     pitch (mm): ", pitch)
            print("     extent (mm): ", extent)
            print("")            

        return N, extent, pitch

    def voxelize_grid(extent, pitch, n, verbose=0):
        #uniform edges of each voxel (1 more than the #of voxels)
        slice_edges = np.linspace(-extent/2, extent/2, n + 1)
        
        #store voxel centers
        coords=(np.arange(n) - (n-1) / 2)*pitch 
        X,Y,Z = np.meshgrid(coords, coords, coords, indexing="ij")
        grid= np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])

        return slice_edges, grid 


    def dip_resampling(dip_data, slice_edges):

        resampled_dips = []
        for dip in dip_data:
            #iterate through each dip i
            dip_id = dip[0, 0]
            theta = dip[0, 1]
            phi = dip[0, 2]
            water_h = dip[:, 3]
            vol_h = dip[:, 4]

            #fit a curve 
            fitted_curve = PchipInterpolator(water_h, vol_h, extrapolate=False)
            heights = np.clip(slice_edges, water_h[0], water_h[-1]) #evaluate only insed measured range (bug with NaN otherwise)
            volumes = fitted_curve(heights)
            
            #assume value above and belwo is no vol chagne
            volumes[slice_edges<water_h[0]] = 0
            volumes[slice_edges>water_h[-1]] = vol_h[-1]
            
            uniform_volumes=np.diff(volumes)
            u = len(uniform_volumes)

            slice = np.column_stack(
                [np.full(u, dip_id),
                np.full(u, theta),
                np.full(u, phi),
                uniform_volumes
                ])

            resampled_dips.append(slice) 
        return np.array(resampled_dips) 
    
    #helper function
    #calculate normal direction from orientations phi,theta (deg)
    def get_normal(theta, phi):
        theta=np.radians(theta) #conver to radians
        phi=np.radians(phi)

        #calculate vector#
        nx=np.sin(theta) * np.cos(phi)
        ny=np.sin(theta)*np.sin(phi)
        nz=np.cos(theta)
        return np.array([nx, ny, nz])
    
    #helper function
    #construct a orthonormal coordinate system aligned with the normal vector
    def get_rotation_basis(theta, phi):
        z = get_normal(theta,phi)
        #find a reference direction not parallel to normal
        ref = np.array([1.0,0.0,0.0])
        if abs(np.dot(ref, z)) > 0.95:
            ref = np.array([0.0,1.0,0.0])

        #get first axis
        x = ref - np.dot(ref, z)*z
        ##normalize x
        x = x/np.linalg.norm(x)
        
        #second plane axis
        y=np.cross(z, x)
        R_basis=np.vstack([x,y,z])
        return R_basis

    #construct the roation operator
    def rotation_theta(theta, phi, n, pitch):
        R_basis=get_rotation_basis(theta,phi)
        N = n**3

        #all output all voxel indices, "using XYZ C-order"
        indices= np.indices((n,n,n))
        indices=indices.reshape(3, -1).T #

        #convrt to coordinates because the object is centered at the origin
        center = (n-1)/2
        voxel_positions = (indices - center) *pitch


        #inverse rotation: output coordinates -> input coords
        rotatated_voxel_positions = voxel_positions @ R_basis

        #convert into fractional voxel indices
        source = rotatated_voxel_positions / pitch +center
        base = np.floor(source).astype(int)
        fraction = source -base

        rows=[]
        cols=[]
        values=[]

        #Trilinear interpolation,check the  8 neighboring voxels
        for offset in product([0,1], repeat=3):
            offset = np.array(offset)
            neighbor=base+offset

            #check which input neighbors are inside the grid
            valid = np.all((neighbor >= 0 )&(neighbor<n), axis=1)

            #interpolation weights 
            weights = np.prod(np.where(offset == 1, fraction, 1-fraction), axis=1)
            #ignore 0 weights
            valid &= weights > 0

            output_ids = np.nonzero(valid)[0]
            input_ids = np.ravel_multi_index(neighbor[valid].T, (n,n,n))

            rows.extend(output_ids)
            cols.extend(input_ids)
            values.extend(weights[valid])

        R_i = coo_matrix((values, (rows, cols)), shape = (N,N)).tocsr()

        return R_i
    
    def rotation_matrix(dip_data, n, pitch):
        #builds one R_theta_k for each dip/orientation
        R = []
        for dip in dip_data:
            theta = dip[0,1]
            phi = dip[0,2]
            R_i= rotation_theta(theta, phi, n, pitch)
            R.append(R_i)

        #stack vertically 
        R = vstack(R, format="csr")
        return R

    def summation_matrix(n, n_dips):
        #one slice is the sum of n*n voxels
        S_bar = kron(csr_matrix(np.ones((1, n*n))), 
                eye(n, format="csr"), 
                format="csr")

        S = block_diag ([S_bar] * n_dips, format = "csr")
        return S

    def sample_matrix(resampled, pitch):
        g = resampled[:,:,3].ravel() #g is individual slice volumes
        g = g / (pitch**3) #note need to normaliye g by the resolution, to match S (output is given in voxel units instead of mm3)
        return g
    
    def solveSystem( B, g, method="LSMR", verbose=0 ):
        if method == "LSMR":
            lam = 0.05 #regularlizration strength

            result = lsmr(B, g, damp=0.0, atol=1e-8, btol=1e-8, maxiter=10000)

            f = result[0]

            if verbose: 
                print("")
                print("LSMR results: ")
                print("     istop: ", result[1])
                print("     itn: ", result[2])
                print("     residual norm: ", result[3])
                print("")  
            return f

    def solution_error(g, f, B):
        g_est = B @ f
        rmse = np.sqrt(np.mean((g_est - g)** 2))
        print("     RMSE: ",rmse)
        return rmse         

    def clamping(f, n, method="otsu", verbose=0):
        threshold = threshold_otsu(f)
        f_binary  = f > threshold
        F_binary = f_binary.reshape(n,n,n) #reshape back into cube grid

        return F_binary
    
    def create_mesh(F_binary, export=1):
        #pad the binary volmes
        object_padded = np.pad(F_binary.astype(float),pad_width=1, mode="constant", constant_values=0)

        #extract the isosurface
        vertices, faces, normals, values = marching_cubes(object_padded, level=0.5, spacing=(pitch,pitch,pitch))

        #create mesh
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=True)

        if export:
            mesh.export("dip_reconstruction.obj")

        return mesh

    
    #   _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ 
 
    
    #Reconstruct the object from the dip data
    #dip_data, k_dips, m_slices

    #1. Voxelize space in cubic grid 
    n = 20 #number of voxels along one axis
    N, extent, pitch = define_gridspace(dip_data, n=n, padding=1.1)
    slice_edges, grid = voxelize_grid(extent, pitch, n)
    
    #2. Uniform resampling
    resampled = dip_resampling(dip_data, slice_edges)

    #3. Inverse optimization
        #i. create rotation matrix R
    R = rotation_matrix(dip_data, n, pitch)
        #ii. create summation matrix S
    S = summation_matrix(n, k_dips)
        #iii. build B = S * R
    B = S @ R
        #iv. build g
    g = sample_matrix(resampled, pitch)
        #v. apply optimization algorithm
    f = solveSystem(B, g)

    #(optional) check quality of f
    #rmse = solution_error(g, f, B)

    #4. Make binary cubic grid
    F_binary = clamping(f, n) 

    #5. create mesh from binary grid 
    mesh = create_mesh(F_binary)



print("\n 3D reconstruction complete. Bio-digital jazz, man. \n")
