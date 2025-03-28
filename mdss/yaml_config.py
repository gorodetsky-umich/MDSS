# This is a yaml configuration file to aid yaml file validation using pydantic
from pydantic import BaseModel, model_validator, ValidationError
from typing import Optional
import yaml
import os
import subprocess

from mdss.helpers import ProblemType, MachineType
class ref_hpc_info(BaseModel):
    cluster: str
    job_name: str
    nodes: int
    nproc: int
    account_name: str
    email_id: str

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
            raise ValueError(f"Invalid parameter combination: {provided_params}.\nMust match one of the following combinations: {valid_combinations}")
        return values

################################################################################
# Aerostructural Specific
################################################################################   
class ref_struct_properties(BaseModel):
    # Material properties
    rho: float=None     # Density in kg/m^3
    E: float=None       # Young's modulus in N/m^2
    nu: float=None      # Poisson's ratio
    kcorr: float=None   # Shear correction factor
    ys: float=None      # Yeild stress

class ref_load_info(BaseModel):
    g: Optional[list[float]]=None
    inertial_load_factor: Optional[float]=None # float, times of 'g', required only if load type is maneuver

class ref_struct_options(BaseModel):
    isym: int # Symmetry direction
    t: float  # Shell thickness in m
    mesh_fpath: str
    properties: Optional[ref_struct_properties]=None
    load_info: Optional[ref_load_info]=None
    solver_options: Optional[dict]=None

class ref_case_info(BaseModel):
    name: str
    problem: str
    meshes_folder_path: str
    mesh_files: list[str]
    geometry_info: ref_geometry_info
    aero_options: dict=None
    struct_options: Optional[ref_struct_options]=None
    scenarios: list[ref_scenario_info]

    @model_validator(mode = 'before')
    def file_existance_checks(cls, values):
        # To Check if correct problem type is assigned
        try:
            cls.problem_type = ProblemType.from_string(values.get('problem'))  # Convert string to enum
        except ValueError:
            raise ValueError(f"Invalid problem type: {values.get('problem')}")
        
        if cls.problem_type == ProblemType.AEROSTRUCTURAL:
            struct_options = values.get("struct_options")
            if not struct_options:
                raise ValidationError("`struct_options` must be provided when running an aerostructural problem")
            
            if not os.path.isfile(struct_options.get("mesh_fpath", "")):
                raise FileNotFoundError(f"Structural Mesh file not found: {struct_options.get('mesh_fpath')}")
        
        return values
    
    @model_validator(mode = 'after')
    def additonal_check(self):
        # To check if the mesh files specifies exists
        for ii, mesh_file in enumerate(self.mesh_files): # Loop for refinement levels to check if the grid files exist
            aero_mesh_file  = os.path.join(os.path.abspath(self.meshes_folder_path), mesh_file)
            if not os.path.isfile(aero_mesh_file):
                raise FileNotFoundError(f"Aero Mesh: {aero_mesh_file} does not exist. Please provide a valid path")
        
        return self


class ref_hierarchy_info(BaseModel):
    name: str
    cases: list[ref_case_info]

class ref_sim_info(BaseModel):
    hierarchies: list[ref_hierarchy_info]
    out_dir: str
    machine_type: str
    hpc_info: Optional[ref_hpc_info]=None
    nproc: Optional[int]=None
    python_version: Optional[str]=None

    @model_validator(mode = 'after')
    def additional_check(self):
        # To Check if correct machine type is assigned
        try:
            self.machine_type = MachineType.from_string(self.machine_type)  # Convert string to enum
        except ValueError:
            raise ValueError(f"Invalid machine type: {self.machine_type}")

        # If running on local machine, ensure nproc is provided as an int. Else if running on a HPC, ensure hpc_info is provided.
        if self.machine_type == MachineType.LOCAL and self.nproc is None:
            raise ValidationError("When running on local machine, 'nproc' must be provided as an integer.")
        elif self.machine_type == MachineType.HPC and self.hpc_info is None:
            raise ValidationError("When running on a cluster,  `hpc_info` must be provided.")
        
        # Aggregate a flag by checking all cases to see if any are aerostructural.
        is_aerostructural = any(
            ProblemType.from_string(case.problem) == ProblemType.AEROSTRUCTURAL
            for hierarchy in self.hierarchies
            for case in hierarchy.cases
        )
        
        if is_aerostructural: # Instead of checking per case, do a one-time module check here.
            try:
                from tacs.mphys import TacsBuilder
                from funtofem.mphys import MeldBuilder
            except ImportError:
                try:
                    subprocess.run(
                        f"{self.python_version} -c 'from tacs.mphys import TacsBuilder; from funtofem.mphys import MeldBuilder'", 
                        shell=True, check=True
                    )
                except:
                    raise ModuleNotFoundError(
                        "TACS and FuntoFEM packages are required for aerostructural problems. "
                        "If available in another Python environment, specify its path in the input YAML under 'python_version'."
                    )
        return self
    
    

            

def check_input_yaml(yaml_file):
    """
    Validates the structure of the input YAML file against predefined templates.

    This function checks whether the input YAML file conforms to the expected template structure. It validates each section, including simulation, HPC, hierarchies, cases, and scenarios.

    Inputs
    ----------
    - **yaml_file** : str
        Path to the YAML file to be validated.

    Outputs
    ------
    **ValidationError**
        If the YAML file does not conform to the expected structure.

    Notes
    -----
    - Uses `ref_sim_info` pydantic model for validation.
    - Ensures hierarchical consistency at all levels of the YAML structure.
    """
    with open(yaml_file, 'r') as file:
        sim_info = yaml.safe_load(file)
    
    ref_sim_info.model_validate(sim_info)
                
                
