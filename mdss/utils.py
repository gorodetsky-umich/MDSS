import copy

from mpi4py import MPI
from enum import Enum
import os
import shutil
import yaml
import importlib.resources as pkg_resources
import random
from pydantic import BaseModel
from typing import Optional, Literal

from mdss.run_sim import run_sim
from mdss.helpers import *


comm = MPI.COMM_WORLD
size = comm.Get_size()

class RunFlag(Enum):
    skip = 0  # Exit without running the simulation
    run = 1   # Run the simulation and populate the data

################################################################################
# Functions to aid pre and post processing
################################################################################
class update_info_file():
    """
    Modifies the input YAML file

    Methods
    -------
    **aero_options()**
        Modifies the aero options in the input file

    **aoa**
        Appends, removes and modifies the Angles of Attack listed in `exp_set`.

    **write_mod_info_file()**
        Writes the modified input file.

    Inputs
    ----------
    - **info_file** : str
        Path to the YAML file containing simulation configuration and information.
    """

    def __init__(self, info_file):
        check_input_yaml(info_file)
        self.info_file = info_file
        self.sim_info = load_yaml_file(self.info_file, comm)

    def aero_options(self, aero_options_updt, case_names):
        '''
        Inputs
        ----------
        - **aero_options_updt** : dict
            A  dictionary containg the aero options to modify.
        
        - **case_names**: list[str]
            A list containing the names of the cases to modify.
            
        '''

        for hierarchy, hierarchy_info in enumerate(self.sim_info['hierarchies']): # loop for Hierarchy level
            for case, case_info in enumerate(hierarchy_info['cases']): # loop for cases in hierarchy
                if case_info['name'] in case_names:
                    case_info['aero_options'].update(aero_options_updt)
    
    def aero_meshes(self, mesh_files, case_names, option,  meshes_folder_path=None):
        '''
        Adds mesh files to specifies cases and optionally modifies the path to the folder contating meshes, when provided.
        Inputs
        ------
        - **mesh_files**: list[str]
            A list containing the mesh file names to append or modify or remove.
        - **case_names**: list[str]
            A list containing the names of the cases to modify.
        - **option**: str
            'a' to append (add the given aoa to the existing list)
            'm' to modify the list (to overwrite)
            'r' to remove the aoa from the file.
        - **meshes_folder_path**: str, optional
            Path to the folder containing meshes
        '''
        for hierarchy, hierarchy_info in enumerate(self.sim_info['hierarchies']): # loop for Hierarchy level
            for case, case_info in enumerate(hierarchy_info['cases']): # loop for cases in hierarchy
                if case_info['name'] in case_names:
                    if option == 'a':
                        case_info['mesh_files'].append(mesh_files)
                    elif option == 'm':
                        case_info['mesh_files'] = [mesh_file for mesh_file in case_info['mesh_files']]
                    elif option == 'r':
                        case_info['mesh_files']= [mesh_file for mesh_file in case_info['mesh_files'] if mesh_file not in mesh_files]
                    if meshes_folder_path is not None:
                        case_info['meshes_folder_path'] = meshes_folder_path

    
    def aoa(self, aoa_list, case_names, exp_sets, option):
        '''
        Inputs
        ----------
        - **aoa_list** : list
            A list containg aoa to append or modify or remove.
        
        - **case_names**: list[str]
            A list containing the names of the cases to modify.
        
        - **exp_sets**: list[int]
            A list containing the `exp_sets` to modify.

        - **option**: str
            'a' to append (add the given aoa to the existing list)
            'm' to modify the list (to overwrite)
            'r' to remove the aoa from the file.
        '''
        for hierarchy, hierarchy_info in enumerate(self.sim_info['hierarchies']): # loop for Hierarchy level
            for case, case_info in enumerate(hierarchy_info['cases']): # loop for cases in hierarchy
                if case_info['name'] in case_names:
                    for exp_set, exp_info in enumerate(case_info['exp_sets']): # loop for experimental datasets that may present
                        if exp_set in exp_sets:
                            if option == 'a':
                                exp_info['aoa_list'] = list(set(exp_info['aoa_list']) | set(aoa_list))  # Convert both to sets to remove duplicates, then back to a list
                            elif option == 'm':
                                exp_info['aoa_list'] = [aoa for aoa in exp_info['aoa_list']]
                            elif option == 'r':
                                exp_info['aoa_list']= [aoa for aoa in exp_info['aoa_list'] if aoa not in aoa_list]
    
    def write_mod_info_file(self, new_fname=None):
        '''
        Inputs
        ----------
        - **fname** : str, Optional
            New file name along with the path. Overwrites the original file, when a new name is not provided.
        '''
        if comm.rank == 0:
            if new_fname is None:
                new_fname = self.info_file
            with open(new_fname, 'w') as info_file_fhandle:
                yaml.dump(self.sim_info, info_file_fhandle, sort_keys=False)

def get_sim_data(info_file):
    """
    Generates a dictionary containing simulation data organized hierarchically.

    This function processes a YAML file with simulation information and creates a
    nested dictionary (`sim_data`) with details about simulation hierarchies, cases,
    experiment sets, refinement levels, and angles of attack.

    Inputs
    ------
    - **info_file** : str
        Path to the input YAML file containing simulation information or configuration.

    Outputs
    -------
    **sim_data**: dict
        A dictionary contating simulation data.
    """
    check_input_yaml(info_file)
    if comm.rank == 0:
        print(f"{'-' * 50}")
        print("YAML file validation is successful")
        print(f"{'-' * 50}")
    info = load_yaml_file(info_file, comm)
    sim_data = {} # Initiating a dictionary to store simulation data

    try:  # Check if the file is overall sim info file and stores the simulation info
        overall_sim_info = info["overall_sim_info"]
        sim_info = copy.deepcopy(info)
        print(f"{'-' * 50}")
        print(f"File provided is an ouput yaml file. Continuing to read data")
        print(f"{'-' * 50}")

    except KeyError:  # if the file is input info file, loads the overall_sim_info.yaml if the simulation is run already
        if comm.rank == 0:
            print(f"{'-' * 50}")
            print(f"File provided is an input yaml file. Checking for existing simulation results in {info['out_dir']}")
            print(f"{'-' * 50}")
        out_yaml_file_path = f"{info['out_dir']}/overall_sim_info.yaml"

        if os.path.isfile(out_yaml_file_path):
            overall_sim_info = load_yaml_file(f"{info['out_dir']}/overall_sim_info.yaml", comm)
        else:
            if comm.rank == 0:
                print(f"{'-' * 50}")
                print(f"No existing simulation found in {info['out_dir']}")
                print(f"{'-' * 50}")
        
    
    # Loop through hierarchy levels
    for hierarchy_index, hierarchy_info in enumerate(overall_sim_info['hierarchies']):
        hierarchy_name = hierarchy_info['name']
        if hierarchy_name not in sim_data:
            sim_data[hierarchy_name] = {}

        # Loop through cases in the hierarchy
        for case_index, case_info in enumerate(hierarchy_info['cases']):
            case_name = case_info['name']
            if case_name not in sim_data[hierarchy_name]:
                sim_data[hierarchy_name][case_name] = {}

            # Loop through experiment sets in the case
            for exp_index, exp_info in enumerate(case_info['exp_sets']):
                exp_set_key = f"exp_set_{exp_index}"
                if exp_set_key not in sim_data[hierarchy_name][case_name]:
                    sim_data[hierarchy_name][case_name][exp_set_key] = {}

                # Loop through mesh files
                for ii, mesh_file in enumerate(case_info['mesh_files']):
                    refinement_level = f"L{ii}"
                    failed_aoa = exp_info['sim_info'][refinement_level]['failed_aoa']
                    if refinement_level not in sim_data[hierarchy_name][case_name][exp_set_key]:
                        sim_data[hierarchy_name][case_name][exp_set_key][refinement_level] = {}

                    # Loop through angles of attack
                    for aoa in exp_info['aoa_list']:
                        if aoa not in failed_aoa:
                            aoa_key = f"aoa_{float(aoa)}"
                            cl = exp_info['sim_info'][refinement_level][aoa_key].get("cl")
                            cd = exp_info['sim_info'][refinement_level][aoa_key].get("cd")

                            # Populate the dictionary
                            if aoa_key not in sim_data[hierarchy_name][case_name][exp_set_key][refinement_level]:
                                sim_data[hierarchy_name][case_name][exp_set_key][refinement_level][aoa_key] = {}

                            sim_data[hierarchy_name][case_name][exp_set_key][refinement_level][aoa_key]['cl'] = cl
                            sim_data[hierarchy_name][case_name][exp_set_key][refinement_level][aoa_key]['cd'] = cd
                    sim_data[hierarchy_name][case_name][exp_set_key][refinement_level]['failed_aoa'] = failed_aoa

    return sim_data

################################################################################
# Functions to run predetermined simulations
################################################################################

class ref_case_info(BaseModel):
    hpc: Optional[Literal['yes', 'no']]='no'
    hpc_info: Optional[dict]=None
    meshes_folder_path: str
    mesh_files: list[str]
    aoa_list: list[float]
    solver_parameters: Optional[dict]=None

class ref_hpc_info:
    job_name: Optional[str]
    nodes: Optional[int]
    nproc: Optional[int]
    account_name: str
    email_id: str


def run_case(case, case_info):
    """
    Run a predefined case simulation.

    This function sets up and executes a simulation based on the provided case information.
    It validates the input, prepares a temporary directory for files, and cleans up after the run.

    Inputs:
    ----------
    case : str
        The name of the simulation case to run (e.g., 'naca0012', '30p-30n').
    case_info : dict
        A dictionary containing the case information. It should follow the structure defined by the `ref_case_info` class:
        - `hpc` Optional(Literal['yes', 'no'])): Indicates whether to run on an HPC cluster ('yes') or locally ('no'). Defatlts to 'no'
        - `hpc_info` (Optional[dict]): If `hpc` is 'yes', this should be a dictionary following the structure of `ref_hpc_info`:
            - `job_name` (Optional[str]): Name of the job.
            - `nodes` (Optional[str]): Number of nodes for the job.
            - `nproc` (Optional[str]): Number of processors for the job.
            - `account_name` (str): HPC account name.
            - `email_id` (str): Email for job notifications.
        - `meshes_folder_path` (str): Path to the directory containing mesh files.
        - `mesh_files` (list[str]): List of mesh file names.
        - `aoa_list` (list[float]): List of angles of attack for the simulation.
        - `solver_parameters` (Optional[dict]): Dictionary of solver-specific parameters (optional).

    Outputs:
    -------
    sim_data : dict
        Simulation results and associated data.

    Notes:
    ------
    - Creates a temporary directory for the simulation input and output files.
    - Deletes the temporary directory after the simulation run.
    """
    ref_case_info.model_validate(case_info)
    # Validate or set default for 'hpc'
    if 'hpc' not in case_info:
        case_info['hpc'] = 'no'

    if case_info['hpc'] == 'yes':
        ref_hpc_info.model_validate(case_info['hpc_info'])
    
    if comm.rank == 0:
        randn = random.randint(1000, 9999)
    else:
        # Other processes initialize the variable
        randn = None
    
    # Broadcast the random number to all processes
    randn = comm.bcast(randn, root=0)
    
    cwd = os.getcwd()
    temp_dir = f"{cwd}/temp_{randn}"
    if comm.rank == 0:
        print(f"{'-' * 50}")
        print("Creating a the temporary folder to run simulations")
        print(f"{'-' * 50}")
        os.mkdir(temp_dir)


    input_file  = f"{case}_simInfo.yaml"
    with pkg_resources.open_text('mdss.resources', input_file) as f:
        sim_info = yaml.safe_load(f)
    try:
        sim_info['hpc'] = case_info['hpc']
    except:
        if comm.rank == 0 and case_info['hpc'] == 'yes':
            print(f"{'-' * 50}")
            print("HPC options are not being updated. Which may cause errors in submission of jobs")
            print(f"{'-' * 50}")

    sim_info['hierarchies'][0]['cases'][0]['meshes_folder_path'] = case_info['meshes_folder_path']
    sim_info['hierarchies'][0]['cases'][0]['mesh_files'] = case_info['mesh_files']
    sim_info['hierarchies'][0]['cases'][0]['exp_sets'][0]['aoa_list'] = case_info['aoa_list']
    try: # As solver parameters are optional.
        sim_info['hierarchies'][0]['cases'][0]['meshes_folder_path'].update(case_info['solver_parameters'])
    except:
        if comm.rank == 0:
            print(f"{'-' * 50}")
            print("Solver parameters are not being updated")
            print(f"{'-' * 50}")
    
    
    
    comm.Barrier()

    if 'out_dir' in case_info:
        sim_info['out_dir'] = case_info['out_dir']
    else:
        sim_info['out_dir'] = f"{cwd}/{temp_dir}/output"
    
    new_input_file = f"{temp_dir}/input.yaml"
    with open(new_input_file, 'w') as f:
        yaml.safe_dump(sim_info, f)

    comm.Barrier()

    # Execute simulation
    sim = run_sim(new_input_file)
    sim.run()
    sim_data = get_sim_data(new_input_file, run_flag=RunFlag.skip)

    comm.Barrier()
    if comm.rank == 0:
        print(f"{'-' * 50}")
        print("Deleting the temporary folder")
        print(f"{'-' * 50}")
        shutil.rmtree(temp_dir)

    return sim_data

def run_naca0012(case_info):
    """
    Run the NACA 0012 simulation case.

    Inputs:
    ----------
    case_info : dict
        A dictionary containing the case information. 

    Outputs:
    -------
    sim_data : dict
        Simulation results and associated data for the NACA 0012 case.

    Notes:
    ------
    - Uses the `run_case` function with 'naca0012' as the case name.
    """
    sim_data = run_case('naca0012', case_info)
    case_data = sim_data['2d_clean']['NACA0012']['exp_set_0']
    return case_data

def run_30p30n(case_info):
    """
    Run the 30p30n simulation case.

    Inputs:
    ----------
    case_info : dict
        A dictionary containing the case information.

    Outputs:
    -------
    sim_data : dict
        Simulation results and associated data for the 30p30n case.

    Notes:
    ------
    - Uses the `run_case` function with '30p-30n' as the case name.
    """
    sim_data = run_case('30p-30n', case_info)
    case_data = sim_data['2d_high_lift']['30p-30n']['exp_set_0']

    return case_data

################################################################################
# Functions to run predetermined simulations
################################################################################

class ref_case_info(BaseModel):
    out_dir: str=None
    meshes_folder_path: str
    mesh_files: list[str]
    aoa_list: list[float]
    aero_options: Optional[dict]=None
    struct_options: dict=None
    
class run_custom_sim():
    """
    Class to Run a predefined case simulation

    It sets up and executes a simulation based on the provided case information.
    It validates the input, prepares a temporary directory for files, and cleans up after the run.

    Inputs:
    ----------
    case : str
        The name of the simulation case to run (e.g., 'naca0012', '30p-30n').
    case_info : dict
        A dictionary containing the case information. It should follow the structure defined by the `ref_case_info` class:
        - `hpc` Optional(Literal['yes', 'no'])): Indicates whether to run on an HPC cluster ('yes') or locally ('no'). Defatlts to 'no'
        - `hpc_info` (Optional[dict]): If `hpc` is 'yes', this should be a dictionary following the structure of `ref_hpc_info`:
            - `job_name` (Optional[str]): Name of the job.
            - `nodes` (Optional[str]): Number of nodes for the job.
            - `nproc` (Optional[str]): Number of processors for the job.
            - `account_name` (str): HPC account name.
            - `email_id` (str): Email for job notifications.
        - `meshes_folder_path` (str): Path to the directory containing mesh files.
        - `mesh_files` (list[str]): List of mesh file names.
        - `aoa_list` (list[float]): List of angles of attack for the simulation.
        - `solver_parameters` (Optional[dict]): Dictionary of solver-specific parameters (optional).

    Outputs:
    -------
    sim_data : dict
        Simulation results and associated data.

    Notes:
    ------
    - Creates a temporary directory for the simulation input and output files.
    - Deletes the temporary directory after the simulation run.
    """
    def __init__(self, name):
        self.resources_dir = None
        if self.resources_dir is None:
            input_file  = f"{name}_simInfo.yaml"
            try:
                with pkg_resources.open_text('mdss.resources', input_file) as f:
                    sim_info = yaml.safe_load(f)
            except:
                err_msg = f"Error: The Simulation Info file for {name} is not available in the package.\nPlease provide a local resources directory path."
                raise FileNotFoundError(err_msg)
        else:
            input_file = os.path.join(os.path.abs(self.resources_dir), f"{name}_simInfo.yaml")
            check_input_yaml(input_file)
            sim_info = load_yaml_file(input_file)
            
        self.sim_info = sim_info
    
    def run(self, case_info):
        '''
        Inputs:
        ----------
        case_info : dict
            A dictionary containing the case information. It should follow the structure defined by the `ref_case_info` class:
            - `meshes_folder_path` (str): Path to the directory containing mesh files.
            - `mesh_files` (list[str]): List of mesh file names.
            - `aoa_list` (list[float]): List of angles of attack for the simulation.
            - `aero_options` (Optional[dict]): Dictionary containing ADflow solver parameters (optional).
            - `struct_options` (Optional[dict]): Dictionary containing structural info for aero structural problem (optional).
        '''
        ref_case_info.model_validate(case_info)
        # Update Info
        self.sim_info['hierarchies'][0]['cases'][0]['meshes_folder_path'] = case_info['meshes_folder_path']
        self.sim_info['hierarchies'][0]['cases'][0]['mesh_files'] = case_info['mesh_files']
        self.sim_info['hierarchies'][0]['cases'][0]['exp_sets'][0]['aoa_list'] = case_info['aoa_list']
        if 'aero_options' in case_info.keys():
            self.sim_info['hierarchies'][0]['cases'][0]['aero_options'].update(case_info['aero_options'])
        if 'struct_options' in case_info.keys():
            self.sim_info['hierarchies'][0]['cases'][0]['struct_options'].update(case_info['struct_options'])

        if comm.rank == 0:
            randn = random.randint(1000, 9999)
        else:
            # Other processes initialize the variable
            randn = None
        
        # Broadcast the random number to all processes
        randn = comm.bcast(randn, root=0)
        cwd = os.getcwd()
        temp_dir = os.path.join(cwd, f"temp_{randn}")
        if comm.rank == 0:
            print(f"{'-' * 50}")
            print("Creating a the temporary folder to run simulations")
            print(f"{'-' * 50}")
            os.mkdir(temp_dir)
        comm.Barrier()
        if 'out_dir' in case_info.keys():
            self.sim_info['out_dir'] = case_info['out_dir']
        else:
            self.sim_info['out_dir'] = temp_dir
        
        new_input_file = f"{temp_dir}/input.yaml"
        with open(new_input_file, 'w') as f:
            yaml.safe_dump(self.sim_info, f)

        comm.Barrier()
        # Execute simulation
        sim = run_sim(new_input_file)
        sim.subprocess_flag = 0 
        sim.run()
        sim_data = get_sim_data(new_input_file)

        comm.Barrier()
        if comm.rank == 0:
            shutil.rmtree(temp_dir)

        return sim_data
        