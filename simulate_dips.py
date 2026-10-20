import trimesh
import numpy as np
import scipy

import plotly.graph_objects as go
import matplotlib.pyplot as plt

import ipywidgets as widgets
from IPython.display import display


    #USER INPUTS
# 1. default shape (sphere, icosehedron, cube) selection or .obj
# 2. voxelization resolution
# 3. number of dips
# 4. number of water height measurements taken per dip 

    #OUTPUTS
# csv
# columns = ["dip no.", "theta", "phi", "water_height_measurement_mm", "displace_vol_mm3"]
 

