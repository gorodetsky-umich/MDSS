# This is a yaml configuration file to aid yaml file validation using pydantic
from pydantic import BaseModel, model_validator, ValidationError
from typing import Optional

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
    mach: Optional[float] = None
    altitude: Optional[float] = None
    reynolds: Optional[float] = None
    T: Optional[float] = None
    P: Optional[float] = None
    rho: Optional[float] = None
    V: Optional[float] = None
    exp_data: Optional[str] = None

    @model_validator(mode='before')
    def check_valid_conditions(cls, values):
        # Define valid parameter combinations
        valid_combinations = [
            {'mach', 'altitude'},
            {'mach', 'reynolds', 'T'},
            {'V', 'reynolds', 'T'},
            {'mach', 'T', 'P'},
            {'mach', 'T', 'rho'},
            {'mach', 'P', 'rho'},
            {'V', 'rho', 'T'},
            {'V', 'rho', 'P'},
            {'V', 'T', 'P'}
        ]

        # Extract provided parameters
        provided_params = {key for key, value in values.items() if value is not None}

        # Check if provided parameters match any valid combination
        if not any(combination <= provided_params for combination in valid_combinations):
            raise ValueError(
                f"Invalid parameter combination: {provided_params}. "
                f"Must match one of the following combinations: {valid_combinations}"
            )
        return values

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
