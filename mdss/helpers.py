import yaml
import pandas as pd
import importlib.resources as resources
import re
from enum import Enum
import os, subprocess, shutil
from mdss.templates import gl_job_script, python_code_for_subprocess, python_code_for_hpc

################################################################################
# Problem types as enum
################################################################################
class ProblemType(Enum):
    """
    Enum representing different types of simulation problems, 
    specifically Aerodynamic and AeroStructural problems.
    
    Attributes
    ----------
        **AERODYNAMIC** (ProblemType): Represents aerodynamic problems with associated aliases.
        **AEROSTRUCTURAL** (ProblemType): Represents aerostructural problems with associated aliases.
    """
    AERODYNAMIC = 1, ["Aerodynamic", "Aero", "Flow"]
    AEROSTRUCTURAL = 2, ["AeroStructural", "Structural", "Combined"]

    def __init__(self, id, aliases):
        self.id = id
        self.aliases = aliases

    @classmethod
    def from_string(cls, problem_name):
        # Match a string to the correct enum member based on aliases
        for member in cls:
            if problem_name in member.aliases:
                return member
        raise ValueError(f"Unknown problem type: {problem_name}")

################################################################################
# Machine types as enum
################################################################################
class MachineType(Enum):
    """
    Enum representing different types of Machines, 
    specifically LOCAL and HPC.
    
    Attributes
    ----------
        **LOCAL** (MachineType): Running the problem on a local machine.
        **AEROSTRUCTURAL** (ProblemType): Running the problem on a High performance computing (HPC) cluster.
    """
    LOCAL = 1, ["LOCAL", "local", "Local", "loc", "Loc", "LOC"]
    HPC = 2, ["hpc", "Hpc", "HPC", "cluster", "Cluster", "CLUSTER"]

    def __init__(self, id, aliases):
        self.id = id
        self.aliases = aliases

    @classmethod
    def from_string(cls, machine_name):
        # Match a string to the correct enum member based on aliases
        for member in cls:
            if machine_name in member.aliases:
                return member
        raise ValueError(f"Unknown machine type: {machine_name}")

################################################################################
# Helper Functions
################################################################################
def print_msg(msg, msg_type, comm=None):
    """
    Prints a formatted message

    Inputs
    ------
    - **msg**: str
        Message to print.
    - **msg_type**: str
        Type of the message to print. Eg., notice, warning etc.,
    - **comm**: MPI communicator, optional
        An MPI communicator object to handle parallelism.
    
    Outputs
    -------
    **None**
    """
    if comm is None or comm.rank == 0:
        print(f"{'-'*50}")
        if msg_type is not None:
            print(f"{msg_type.upper():^50}")
            print(f"{'-'*50}")
        print(f"{msg}")
        print(f"{'-'*50}")

def make_dir(dir_path, comm=None):
    """
    Checks if the directory already exists and create when it does not.

    Inputs
    ------
    - **dir_path:** str,
        Path to the directory to create.
     - **comm**: MPI communicator, optional
        An MPI communicator object to handle parallelism.

    Outputs
    -------
    **None**
    """
    if not os.path.exists(dir_path): # Create the directory if it doesn't exist
        if comm is None or comm.rank == 0:
            os.makedirs(dir_path)

def load_yaml_file(yaml_file, comm):
    """
    Loads a YAML file and returns its content as a dictionary.

    This function attempts to read the specified YAML file and parse its content into a Python dictionary. If the file cannot be loaded due to errors, it provides a detailed error message.

    Inputs
    ------
    - **yaml_file** : str
        Path to the YAML file to be loaded.
    - **comm** : MPI communicator  
        An MPI communicator object to handle parallelism.

    Outputs
    -------
    **dict or None**
        A dictionary containing the content of the YAML file if successful, or None if an error occurs.
    """
    try:
        # Attempt to open and read the YAML file
        with open(yaml_file, 'r') as file:
            dict_info = yaml.safe_load(file)
        return dict_info
    except FileNotFoundError:
        # Handle the case where the YAML file is not found
        if comm.rank == 0:  # Only the root process prints this error
            print(f"FileNotFoundError: The info file '{yaml_file}' was not found.")
    except yaml.YAMLError as ye:
        # Errors in YAML parsing
        if comm.rank == 0:  # Only the root process prints this error
            print(f"YAMLError: There was an issue reading '{yaml_file}'. Check the YAML formatting. Error: {ye}")
    except Exception as e:
        # General error catch in case of other unexpected errors
        if comm.rank == 0:  # Only the root process prints this error
            print(f"An unexpected error occurred while loading the info file: {e}")
    return None

def load_csv_data(csv_file, comm):
    """
    Loads a CSV file and returns its content as a Pandas DataFrame.

    This function reads the specified CSV file and converts its content into a Pandas DataFrame. It handles common errors such as missing files, empty files, or parsing issues.

    Inputs
    ----------
    - **csv_file** : str
        Path to the CSV file to be loaded.
    - **comm** : MPI communicator  
        An MPI communicator object to handle parallelism.
    Outputs
    -------
    **pandas.DataFrame or None**
        A DataFrame containing the content of the CSV file if successful, or None if an error occurs.
"""
    try:
        df = pd.read_csv(csv_file)
        df.columns = df.columns.str.strip()  # Remove extra whitespace in column names
        for col in ['Alpha', 'CL', 'CD']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        # Drop rows that have NaN in any of the expected columns
        required_cols = [col for col in ['Alpha', 'CL', 'CD'] if col in df.columns]
        df = df.dropna(subset=required_cols)

        return df
    except FileNotFoundError:
        if comm.rank == 0:
            print(f"Warning: The file '{csv_file}' was not found. Please check the file path.")
    except pd.errors.EmptyDataError:
        if comm.rank == 0:
            print("Error: The file is empty. Please check if data has been written correctly.")
    except pd.errors.ParserError:
        if comm.rank == 0:
            print("Error: The file could not be parsed. Please check the file format.")
    except Exception as e:
        if comm.rank == 0:
            print(f"An unexpected error occurred: {e}")
    return None # In case of error, return none.

def submit_job_on_hpc(sim_info, yaml_file_path, comm):
    """
    Generates and submits job script on an HPC cluster.

    This function reads a slurm job script template, updates it with specific HPC parameters and file paths, saves the customized script to the output directory, and submits the job on the HPC cluster.

    Inputs
    ------
    - **sim_info** : dict
        Dictionary containing simulation details details.
    - **yaml_file_path** : str
        Path to the YAML file containing simulation information.
    - **comm** : MPI communicator  
        An MPI communicator object to handle parallelism.


    Outputs
    -------
    - **None**

    Notes
    -----
    - Supports customization for the GL cluster with Slurm job scheduling.
    - Uses regex to update the job script with provided parameters.
    - Ensures that the correct Python and YAML file paths are embedded in the job script.
    """
    out_dir = os.path.abspath(sim_info['out_dir'])
    hpc_info = sim_info['hpc_info'] # Extract HPC info
    python_fname = os.path.join(out_dir, "run_sim.py") # Python script to be run on on HPC
    out_file = os.path.join(out_dir, f"{hpc_info['job_name']}_job_out.txt")
    
    if hpc_info['cluster'] == 'GL':
        job_time = hpc_info.get('time', '1:00:00')  # Set default time if not provided
        mem_per_cpu = hpc_info.get('mem_per_cpu', '1000m')

        # Fill in the template of the job script(can be found in `templates.py`) with values from hpc_info, provided by the user
        job_script = gl_job_script.format(
            job_name=hpc_info['job_name'],
            nodes=hpc_info['nodes'],
            nproc=hpc_info['nproc'],
            mem_per_cpu=mem_per_cpu,
            time=job_time,
            account_name=hpc_info['account_name'],
            email_id=hpc_info['email_id'],
            out_file=out_file,
            python_file_path=python_fname,
            yaml_file_path=yaml_file_path
        )
        
        job_script_path = os.path.join(out_dir, f"{hpc_info['job_name']}_job_file.sh") # Define the path for the job script

        if comm.rank==0:
            with open(job_script_path, "w") as file: # Save the job script to be submitted on great lakes
                file.write(job_script)

            with open(python_fname, "w") as file: # Write the python file(can be found in `templates.py`) to be run using the above created job script.
                file.write(python_code_for_hpc)
            
            subprocess.run(["sbatch", job_script_path]) # Subprocess to submit the job script on Great Lakes
        return
    
################################################################################
# Helper Functions for running the simulations as subprocesses
################################################################################
def run_as_subprocess(sim_info, case_info_fpath, scenario_info_fpath, ref_out_dir, aoa_csv_string, aero_grid_fpath, struct_mesh_fpath, comm, record_flag=False):
    """
    Executes a set of Angles of Attack using mpirun for local machine and srun for HPC(Great Lakes).

    Inputs
    ------
    - **sim_info** : dict  
        Dictionary containing simulation details, such as output directory, job name, and nproc.
    - **case_info_fpath** : str  
        Path to the case info yaml file
    - **scenario_info_fpath** : str  
        Path to the scenario info yaml file
    - **ref_out_dir** : str  
        Path to the refinement level directory
    - **aoa_csv_string** : str 
        A list of angles of attack, in the form of csv string, that to be simulated in this subprocess
    - **aero_grid_fpath** : 
        Path to the aero grid file that to be used for this simulation.
    - **struct_mesh_fpath**: str
        Path to the structural mesh file that to be used. Pass str(None) when running aero problem.
    - **comm** : MPI communicator  
        An MPI communicator object to handle parallelism.
    - **record_flag**: bool=False, Optional
        Optional flag, strores ouput of the subprocess in a text file.

    Outputs
    -------
    - **None**  
        This function does not return any value but performs the following actions:
        1. Creates necessary directories and input files.
        2. Launches a subprocess to execute the simulation using `mpirun` or `srun`.
        3. Prints standard output and error logs from the subprocess for debugging.

    Notes
    -----
    - The function ensures the proper setup of the simulation environment for the given angle of attack.
    - The generated Python script and YAML input file are specific to each simulation run.
    - Captures and displays `stdout` and `stderr` from the subprocess for troubleshooting.
    """
    out_dir = os.path.abspath(sim_info['out_dir'])
    python_fname = os.path.join(out_dir, "script_for_subprocess.py")
    machine_type = MachineType.from_string(sim_info['machine_type'])
    subprocess_out_file = os.path.join(os.path.dirname(scenario_info_fpath), "subprocess_out.txt")
    shell = False

    if not os.path.exists(python_fname): # Saves the python script, that is used to run subprocess in the output directory, if the file do not exist already.
        if comm.rank==0:
            with open(python_fname, "w") as file: # Open the file in write mode
                file.write(python_code_for_subprocess)

    env = os.environ.copy()
    
    python_version = sim_info.get('python_version', 'python') # Update python with user defined version or defaults to current python version
    if shutil.which(python_version) is None: # Check if the python executable exists
        python_version = 'python'
        if comm.rank == 0:
            print(f"Warning: {python_version} not found! Falling back to default 'python'.")
    if comm.rank==0:
        print(f"{'-' * 30}")
        print(f"Starting subprocess for the following aoa: {aoa_csv_string}")
        if machine_type==MachineType.LOCAL:
            nproc = sim_info['nproc']
            run_cmd = ['mpirun', '-np', str(nproc), python_version]
            
        elif machine_type==MachineType.HPC:
            run_cmd = ['srun', python_version]
        run_cmd.extend([python_fname, '--caseInfoFile', case_info_fpath, '--scenarioInfoFile', scenario_info_fpath, 
                '--refLevelDir', ref_out_dir, '--aoaList', aoa_csv_string, '--aeroGrid', aero_grid_fpath, '--structMesh', struct_mesh_fpath])

        p = subprocess.Popen(run_cmd, 
            env=env,
            stdout=subprocess.PIPE,  # Capture standard output
            stderr=subprocess.PIPE,  # Capture standard error
            text=True,  # Ensure output is in text format, not bytes
            )
        
        # Read and print the output and error messages
        stdout, stderr = p.communicate()
        # Write output to file manually
        if record_flag is True:
            with open(subprocess_out_file, 'a') as f:
                f.write(stdout)
                f.write(stderr)
        # Print subprocess outptut
        print("Subprocess Output:", stdout)
        print("Subprocess Error:", stderr)

        p.wait() # Wait for subprocess to end
        
        print(f"Completed")
        print(f"{'-' * 30}")

################################################################################
# Helper Functions to update openmdao instance
################################################################################
class update_om_instance:
    '''
    Modifies some options in the openmdao instance

    Methods
    -------
    **outdir()**
        Modifies the output directory to save the output files from aero and structural solvers.

    **aero_options()**
        Updates the aero_options in the aero solver.

    Inputs
    ----------
    - **prob** : openmdao instance
        An instance openmdao class to be modified
    '''
    def __init__(self, prob, scenario, problem):
        self.prob = prob
        self.scenario = scenario
        self.scenario_attr = getattr(self.prob.model, self.scenario)
        # Assign problem type
        try:
            self.problem_type = ProblemType.from_string(problem)  # Convert string to enum
        except ValueError as e:
            print(e)

    def outdir(self, new_outdir):
        '''
        Inputs:
        -------
        - **new_outdir**: str
            New output directory to save the output files
        '''
        if self.problem_type == ProblemType.AERODYNAMIC:
            self.scenario_attr.coupling.options['solver'].options['outputDirectory'] = new_outdir
        elif self.problem_type == ProblemType.AEROSTRUCTURAL:
            self.scenario_attr.coupling.aero.options['solver'].options['outputDirectory'] = new_outdir
            self.scenario_attr.struct_post.eval_funcs.sp.setOption('outputdir', new_outdir)
    
    def aero_options(self, new_aero_options):
        # Currently do not work
        """
        Inputs:
        -------
        - **new_aero_options**: dict
            New aero_options to update
        """
        if self.problem_type == ProblemType.AERODYNAMIC:
            self.scenario_attr.aero_post.options['solver'].options.update(new_aero_options)
        elif self.problem_type == ProblemType.AEROSTRUCTURAL:
            for key, value in new_aero_options.items():
                try:
                    print(key, value)
                    self.scenario_attr.aero_post.options['aero_solver'].options[key] = value
                    self.scenario_attr.coupling.aero.options['solver'].options[key] = value
                except:
                    print_msg(f"{key} not found", 'warning')

################################################################################
# Function to perform deep update
################################################################################
def deep_update(base_dict, update_dict):
    """
    Recursively updates the base_dict with values from update_dict.

    For keys present in both dictionaries:
        - If the values are both dicts, perform a recursive deep update.
        - Otherwise, the value from `update_dict` overwrites the one in `base_dict`.

    Inputs:
    -------
    - base_dict: dict
        The dictionary to be updated.
    - update_dict: dict
        The dictionary whose values will be merged into base_dict.
    """
    for key, value in update_dict.items():
        if key in base_dict:
            # Handle dict of dicts
            if isinstance(base_dict[key], dict) and isinstance(value, dict):
                deep_update(base_dict[key], value)
            # Handle list of dicts with 'name' keys
            elif isinstance(base_dict[key], list) and isinstance(value, list):
                if all(isinstance(i, dict) for i in base_dict[key] + value):
                    # Merge list items based on 'name' key
                    base_items = {item['name']: item for item in base_dict[key]}
                    for item in value:
                        name = item['name']
                        if name in base_items:
                            deep_update(base_items[name], item)
                        else:
                            base_dict[key].append(item)
                else:
                    base_dict[key] = value  # fallback
            else:
                base_dict[key] = value
        else:
            base_dict[key] = value

################################################################################
# Additional Data Types
################################################################################
class DeepDict(dict):
    """
    A subclass of Python's built-in dict that supports recursive (deep) updates
    and merging of nested dictionaries.

    This class provides a `deep_update` method that merges nested dictionaries
    without overwriting inner dictionaries, as well as a static `merge` method
    and support for the `+` operator to perform deep merging.

    Example:
    --------

        >>> d1 = DeepDict({'a': {'x': 1}, 'b': 2})
        >>> d2 = {'a': {'y': 3}, 'c': 4}
        >>> d1.deep_update(d2)
        >>> print(d1)
        {'a': {'x': 1, 'y': 3}, 'b': 2, 'c': 4}

        >>> d3 = DeepDict({'p': {'q': 1}})
        >>> d4 = {'p': {'r': 2}}
        >>> merged = d3 + d4
        >>> print(merged)
        {'p': {'q': 1, 'r': 2}}
    """

    def deep_update(self, other):
        """
        Recursively updates the dictionary with another dictionary.

        For keys present in both dictionaries:
            - If the values are both dicts, perform a recursive deep update.
            - Otherwise, the value from `other` overwrites the one in `self`.

        Inputs:
        -------
        - *other*: dict
            Dictionary to merge into this one.
        """
        for key, value in other.items():
            if (
                key in self and isinstance(self[key], dict)
                and isinstance(value, dict)
            ):
                if not isinstance(self[key], DeepDict):
                    self[key] = DeepDict(self[key])
                self[key].deep_update(value)
            else:
                self[key] = value

    @staticmethod
    def merge(dict1, dict2):
        """
        Returns a new DeepDict that is the deep merge of `dict1` and `dict2`.

        The original dictionaries remain unmodified.

        Inputs:
        -------
        - *dict1*: dict
            The base dictionary.
        - *dict12*: dict
            The dictionary to merge into the base.

        Outputs:
        --------
        - *DeepDict*: A new dictionary that is the deep merge of both.
        """
        result = DeepDict(dict1)
        result.deep_update(dict2)
        return result

    def __add__(self, other):
        """
        Implements the + operator to perform a deep merge of two dictionaries.

        Inputs:
        -------
        - *other*: dict
            The dictionary to merge with.

        Outputs:
        --------
        - *DeepDict*: A new DeepDict instance with the merged contents.
        """
        if not isinstance(other, dict):
            raise TypeError("Can only add another dict or DeepDict")
        return DeepDict.merge(self, other)

        