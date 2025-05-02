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

from mdss.src.main import simulation
from mdss.utils.helpers import *
from mdss.resources.yaml_config import check_input_yaml


comm = MPI.COMM_WORLD
size = comm.Get_size()

class RunFlag(Enum):
    skip = 0  # Exit without running the simulation
    run = 1   # Run the simulation and populate the data

################################################################################
# Functions to aid pre and post processing
################################################################################
class update_yaml_input():
    """
    Modifies the YAML input.

    Inputs
    ------
    - **info_file** : str
        Path to the YAML file containing simulation configuration and information.
    """

    def __init__(self, yaml_input):
        check_input_yaml(yaml_input)

        self.sim_info, self.yaml_input_type = load_yaml_input(yaml_input, comm)
        self.out_dir = self.sim_info['out_dir']
        if self.yaml_input_type == YAMLInputType.FILE:
            self.info_file = yaml_input
        elif self.yaml_input_type == YAMLInputType.STRING:
            self.info_file = os.path.join(self.out_dir, "input.yaml")
            with open(self.info_file, 'w') as f:
                yaml.dump(self.sim_info, f, sort_keys=False)
        

    def aero_options(self, aero_options_updt, case_names):
        """
        Modifies the aero options in the YAML input.

        Inputs
        ------
        - **aero_options_updt** : dict
            A  dictionary containg the aero options to modify.
        
        - **case_names**: list[str]
            A list containing the names of the cases to modify.
            
        """

        for hierarchy, hierarchy_info in enumerate(self.sim_info['hierarchies']): # loop for Hierarchy level
            for case, case_info in enumerate(hierarchy_info['cases']): # loop for cases in hierarchy
                if case_info['name'] in case_names:
                    case_info['aero_options'].update(aero_options_updt)
    
    def aero_meshes(self, mesh_files, case_names, option,  meshes_folder_path=None):
        """
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
        """
        for hierarchy, hierarchy_info in enumerate(self.sim_info['hierarchies']): # loop for Hierarchy level
            for case, case_info in enumerate(hierarchy_info['cases']): # loop for cases in hierarchy
                if case_info['name'] in case_names:
                    if option == 'a':
                        case_info['mesh_files'].extend(mesh_files)
                    elif option == 'm':
                        case_info['mesh_files'] = mesh_files
                    elif option == 'r':
                        case_info['mesh_files']= [mesh_file for mesh_file in case_info['mesh_files'] if mesh_file not in mesh_files]
                    if meshes_folder_path is not None:
                        case_info['meshes_folder_path'] = meshes_folder_path

    
    def aoa(self, aoa_list, case_names, scenario_names, option):
        """
        Appends, removes and modifies the Angles of Attack listed in `scenario`.

        Inputs
        ------
        - **aoa_list** : list
            A list containg aoa to append or modify or remove.
        
        - **case_names**: list[str]
            A list containing the names of the cases to modify.
        
        - **scenario_names**: list[str]
            A list containing the name of the scenarios to modify.

        - **option**: str
            'a' to append (add the given aoa to the existing list)
            'm' to modify the list (to overwrite)
            'r' to remove the aoa from the file.
        """
        for hierarchy, hierarchy_info in enumerate(self.sim_info['hierarchies']): # loop for Hierarchy level
            for case, case_info in enumerate(hierarchy_info['cases']): # loop for cases in hierarchy
                if case_info['name'] in case_names:
                    for scenario, scenario_info in enumerate(case_info['scenarios']): # loop for scenarios that may present
                        if scenario_info['name'] in scenario_names:
                            if option == 'a':
                                scenario_info['aoa_list'] = list(set(scenario_info['aoa_list']) | set(aoa_list))  # Convert both to sets to remove duplicates, then back to a list
                            elif option == 'm':
                                scenario_info['aoa_list'] = aoa_list
                            elif option == 'r':
                                scenario_info['aoa_list']= [aoa for aoa in scenario_info['aoa_list'] if aoa not in aoa_list]

    def write_mod_info_file(self, new_fname=None):
        """
         Writes the modified input file.

        Inputs
        ------
        - **fname** : str, Optional
            New file name along with the path. Overwrites the original file, when a new name is not provided.
        """
        if comm.rank == 0:
            if new_fname is None:
                new_fname = self.info_file
            with open(new_fname, 'w') as info_file_fhandle:
                yaml.dump(self.sim_info, info_file_fhandle, sort_keys=False)

    def return_yaml_string(self):
        """
        Returns the YAML string representation of the simulation information.
        """
        return yaml.dump(self.sim_info, sort_keys=False)

class update_sim_info(update_yaml_input):
    def __init__(self, sim_info: dict):
        check_input_yaml(yaml.dump(sim_info))
        self.sim_info = sim_info
        self.out_dir = self.sim_info['out_dir']
        self.info_file = os.path.join(self.out_dir, "input.yaml")
        with open(self.info_file, 'w') as f:
            yaml.dump(self.sim_info, f, sort_keys=False)
        

def get_sim_data(yaml_input):
    """
    Generates a dictionary containing simulation data organized hierarchically.

    This function processes a YAML file with simulation information and creates a
    nested dictionary (`sim_data`) with details about simulation hierarchies, cases,
    scenarios, refinement levels, and angles of attack.

    Inputs
    ------
    - **yaml_input** : str
        Path to the input YAML file or raw YAML string containing simulation information or configuration.

    Outputs
    -------
    **sim_data**: dict
        A dictionary containing simulation data.
    """
    check_input_yaml(yaml_input)
    msg = f"YAML file validation is successful"
    print_msg(msg, 'notice', comm)
    sim_info,_ = load_yaml_input(yaml_input, comm)
    sim_data = {} # Initiating a dictionary to store simulation data

    if 'overall_sim_info' in sim_info.keys():  # if the file is output info file, loads the overall_sim_info.yaml
        print_msg(f"File provided is an ouput yaml file. Continuing to read data", 'notice', comm)
        overall_sim_info = sim_info
    else:
        print_msg(f"File provided is an input yaml file. Checking for existing simulation results in {sim_info['out_dir']}", 'notice', comm)
        out_yaml_file_path = f"{sim_info['out_dir']}/overall_sim_info.yaml"
        if os.path.isfile(out_yaml_file_path):
            overall_sim_info,_ = load_yaml_input(f"{sim_info['out_dir']}/overall_sim_info.yaml", comm)
        else:
            raise FileNotFoundError(f"File {out_yaml_file_path} simulation results not found. Please run the simulation.")

    sim_data['overall_sim_info'] = overall_sim_info.get('overall_sim_info', {})
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

            # Loop through scenarios in the case
            for scenario_index, scenario_info in enumerate(case_info['scenarios']):
                scenario_name = scenario_info['name']
                if scenario_info['name'] not in sim_data[hierarchy_name][case_name]:
                    sim_data[hierarchy_name][case_name][scenario_name] = {}

                # Loop through mesh files
                for ii, mesh_file in enumerate(case_info['mesh_files']):
                    failed_aoa = scenario_info['sim_info'][mesh_file]['failed_aoa']
                    if mesh_file not in sim_data[hierarchy_name][case_name][scenario_name]:
                        sim_data[hierarchy_name][case_name][scenario_name][mesh_file] = {}

                    # Loop through angles of attack
                    for aoa in scenario_info['aoa_list']:
                        if aoa not in failed_aoa:
                            aoa_key = f"aoa_{float(aoa)}"
                            sim_data[hierarchy_name][case_name][scenario_name][mesh_file][aoa_key]= scenario_info['sim_info'][mesh_file].get(aoa_key,{})

                    sim_data[hierarchy_name][case_name][scenario_name][mesh_file]['failed_aoa'] = failed_aoa

    return sim_data

################################################################################
# Functions to run predetermined simulations
################################################################################

class ref_case_info(BaseModel):
    out_dir: str=None
    meshes_folder_path: Optional[str]=None
    mesh_files: Optional[list[str]]=None
    aoa_list: list[float]
    aero_options: Optional[dict]=None
    struct_options: Optional[dict]=None
    
class custom_sim(simulation):
    """
    Class to Run a predefined case simulation

    It sets up and executes a simulation based on the provided case information.
    It validates the input, prepares a temporary directory for files, and cleans up after the run.

    Inputs
    ------
    - **yaml_input**: str
        The YAML file path or raw YAML string for the simulation.

    Notes
    ------
    - Creates a temporary directory for the simulation input and output files.
    - Deletes the temporary directory after the simulation run.
    """
    def __init__(self, yaml_input:str, out_dir:str=None):
        super().__init__(yaml_input)  # Leverages validation, parsing, and setup from `simulation`
        if comm.rank == 0:
            if os.path.exists(self.sim_info['out_dir']) and not os.listdir(self.sim_info['out_dir']):  # Check if the output directory exits and is empty
                os.rmdir(self.sim_info['out_dir'])  # Remove the directory only if it is empty
    
    def run(self, case_info):
        """
        Inputs
        ----------
        - **case_info**: dict
            A dictionary containing the case information. It should follow the structure defined by the `ref_case_info` class:
            - `out_dir` (str): Path to the output directory.
            - `meshes_folder_path` (str): Path to the directory containing mesh files.
            - `mesh_files` (list[str]): List of mesh file names.
            - `aoa_list` (list[float]): List of angles of attack for the simulation.
            - `aero_options` (Optional[dict]): Dictionary containing ADflow solver parameters (optional).
            - `struct_options` (Optional[dict]): Dictionary containing structural info for aero structural problem (optional).
        """
        ref_case_info.model_validate(case_info)
        
        case = self.sim_info['hierarchies'][0]['cases'][0]
        scenario = case['scenarios'][0]
        case_info['aoa_list'] = [float(aoa) for aoa in case_info['aoa_list']]  # Ensures all angles of attack to float and converts a numpy array to a list
        # Extract only fields that were explicitly provided (non-None)
        for key, value in case_info.items():
            if value is None:
                continue  # Skip unset or None fields
            if key == 'aoa_list':
                scenario['aoa_list'] = value
            elif key in {'aero_options', 'struct_options'}:
                case.setdefault(key, {}).update(value)
            else:
                case[key] = value

        if comm.rank == 0:
            randn = random.randint(1000, 9999)
        else:
            # Other processes initialize the variable
            randn = None
        
        # Broadcast the random number to all processes
        randn = comm.bcast(randn, root=0)
        cwd = os.getcwd()
        if 'out_dir' in case_info.keys():
            if not os.path.exists(case_info['out_dir']) and comm.rank == 0:
                os.mkdir(case_info['out_dir'])
            self.sim_info['out_dir'] = case_info['out_dir']
            self.out_dir = case_info['out_dir']
        else:
            temp_dir = os.path.join(cwd, f"temp_{randn}")
            msg = f"Creating a temporary folder to run simulations: {temp_dir}"
            print_msg(msg, 'notice', comm)
            if comm.rank == 0:
                os.mkdir(temp_dir)
            self.sim_info['out_dir'] = temp_dir
            self.out_dir = temp_dir
        comm.Barrier()
        self.final_out_file = os.path.join(self.out_dir, "overall_sim_info.yaml")  # Set the final output file path
        modified_yaml_input = yaml.dump(self.sim_info, sort_keys=False)
        check_input_yaml(modified_yaml_input)  # Validate the modified YAML input
        # Write the modified YAML input to a file
        if not os.path.exists(self.out_dir):
            if comm.rank == 0:
                os.mkdir(self.out_dir)
        self.info_file = os.path.join(self.out_dir, "input.yaml")  # Set the path for the input YAML file
        with open(self.info_file, 'w') as f:
            yaml.dump(self.sim_info, f, sort_keys=False)

        if self.machine_type == MachineType.HPC:
            self.wait_for_job = True # To toggle to wait for the job to finish.
            
        # Call the parent class's run method to execute the simulation
        super().run()  

        # Read the simulation data from the final output file
        if os.path.exists(self.final_out_file):
            sim_data = get_sim_data(self.final_out_file)

        # Cleanup temp directory if created
        if 'out_dir' not in case_info and comm.rank == 0:
            shutil.rmtree(self.out_dir)

        return sim_data
        