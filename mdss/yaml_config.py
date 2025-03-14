# This is a yaml configuration file to aid yaml file validation using pydantic
from pydantic import BaseModel

class ref_sim_info(BaseModel):
    hierarchies: list[dict]
    out_dir: str
    hpc: str
    nproc: int=None

class ref_hpc_info(BaseModel):
    cluster: str
    job_name: str
    nodes: int
    nproc: int
    account_name: str
    email_id: str


class ref_hierarchy_info(BaseModel):
    name: str
    cases: list

class ref_case_info(BaseModel):
    name: str
    problem: str
    meshes_folder_path: str
    mesh_files: list[str]
    geometry_info: dict
    aero_options: dict=None
    struct_options: dict=None
    scenarios: list

class ref_geometry_info(BaseModel):
    chordRef: float
    areaRef: float

class ref_scenario_info(BaseModel):
    name: str
    aoa_list: list[float]
    Re: float
    mach: float
    Temp: float
    exp_data: str=None

################################################################################
# Aerostructural Specific
################################################################################
class ref_struct_options(BaseModel):
    isym: int
    mesh_fpath: str
    properties: dict=None
    load_info: dict
    
class ref_struct_properties(BaseModel):
    # Material properties
    rho: float=None     # Density in kg/m^3
    E: float=None       # Young's modulus in N/m^2
    nu: float=None      # Poisson's ratio
    kcorr: float=None   # Shear correction factor
    ys: float=None      # Yeild stress

    # Shell Thickness
    t: float=None       # in m

class ref_load_info(BaseModel):
    load_type: str
