# Imports
import yaml, os
import pandas as pd
from enum import Enum
from pathlib import Path

################################################################################
# Problem types as enum
################################################################################
class ProblemType(Enum):
    """
    Enum representing different types of simulation problems, 
    specifically Aerodynamic and AeroStructural problems.
    
    Attributes
    ----------
    - **AERODYNAMIC** (ProblemType): Represents aerodynamic problems with associated aliases.
    - **AEROSTRUCTURAL** (ProblemType): Represents aerostructural problems with associated aliases.
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
    - **LOCAL** (MachineType): Running the problem on a local machine.
    - **HPC** (MachineType): Running the problem on a High performance computing (HPC) cluster.
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
    - **dict or None**
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
    - **pandas.DataFrame or None**
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
        """
        Inputs
        -------
        - **new_outdir**: str
            New output directory to save the output files
        """
        if self.problem_type == ProblemType.AERODYNAMIC:
            self.scenario_attr.coupling.options['solver'].options['outputDirectory'] = new_outdir
        elif self.problem_type == ProblemType.AEROSTRUCTURAL:
            self.scenario_attr.coupling.aero.options['solver'].options['outputDirectory'] = new_outdir
            self.scenario_attr.struct_post.eval_funcs.sp.setOption('outputdir', new_outdir)
    
    def restart_file(self, new_restart_file):
        """
        Inputs
        -------
        - **new_restart_file**: str
            New file to restart simulation.
        """
        if self.problem_type == ProblemType.AERODYNAMIC:
            self.scenario_attr.coupling.options['solver'].options['restartFile'] = new_restart_file
        elif self.problem_type == ProblemType.AEROSTRUCTURAL:
            self.scenario_attr.coupling.aero.options['solver'].options['restartFile'] = new_restart_file

    def aero_options(self, new_aero_options):
        # Currently do not work
        """
        Inputs
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

    Inputs
    -------
    - **base_dict**: dict
        The dictionary to be updated.
    - **update_dict**: dict
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
# Function to check and return volume files for restart
################################################################################
def get_restart_file(search_dir):
    """
    Find the appropriate CGNS restart file from the given directory.

    Inputs
    ------
    - **search_dir**: str or Path
        Directory where restart files are located (currently overridden inside function).
    - **comm**: MPI communicator  
        An MPI communicator object to handle parallelism.

    Outputs
    -------
    - vol_cgns_path : Path or None
        Path to the selected CGNS restart file:
        - Preferably a file ending in '_vol.cgns' that does not contain 'failed'
        - Falls back to one containing 'failed' if no preferred file exists
        - Returns None if no such file is found
    """
    if not os.path.exists(search_dir):
        return None
    search_dir = Path(search_dir)
    # Get all files ending with _vol.cgns
    vol_cgns_files = [f for f in search_dir.iterdir() if f.name.endswith("_vol.cgns")]

    # Separate them into preferred and failed
    preferred_files = [f for f in vol_cgns_files if 'failed' not in f.name]
    failed_files = [f for f in vol_cgns_files if 'failed' in f.name]

    # Choose the preferred one if it exists, else fallback to the failed one
    vol_cgns_path = preferred_files[0] if preferred_files else (failed_files[0] if failed_files else None)
    
    return vol_cgns_path
    
################################################################################
# Additional Data Types
################################################################################
# class DeepDict(dict):
#     """
#     A subclass of Python's built-in dict that supports recursive (deep) updates
#     and merging of nested dictionaries.

#     This class provides a `deep_update` method that merges nested dictionaries
#     without overwriting inner dictionaries, as well as a static `merge` method
#     and support for the `+` operator to perform deep merging.

#     Example:
#     --------

#         >>> d1 = DeepDict({'a': {'x': 1}, 'b': 2})
#         >>> d2 = {'a': {'y': 3}, 'c': 4}
#         >>> d1.deep_update(d2)
#         >>> print(d1)
#         {'a': {'x': 1, 'y': 3}, 'b': 2, 'c': 4}

#         >>> d3 = DeepDict({'p': {'q': 1}})
#         >>> d4 = {'p': {'r': 2}}
#         >>> merged = d3 + d4
#         >>> print(merged)
#         {'p': {'q': 1, 'r': 2}}
#     """

#     def deep_update(self, other):
#         """
#         Recursively updates the dictionary with another dictionary.

#         For keys present in both dictionaries:
#             - If the values are both dicts, perform a recursive deep update.
#             - Otherwise, the value from `other` overwrites the one in `self`.

#         Inputs
#         -------
#         - **other**: dict
#             Dictionary to merge into this one.
#         """
#         for key, value in other.items():
#             if (
#                 key in self and isinstance(self[key], dict)
#                 and isinstance(value, dict)
#             ):
#                 if not isinstance(self[key], DeepDict):
#                     self[key] = DeepDict(self[key])
#                 self[key].deep_update(value)
#             else:
#                 self[key] = value

#     @staticmethod
#     def merge(dict1, dict2):
#         """
#         Returns a new DeepDict that is the deep merge of `dict1` and `dict2`.

#         The original dictionaries remain unmodified.

#         Inputs
#         -------
#         - **dict1**: dict
#             The base dictionary.
#         - **dict12**: dict
#             The dictionary to merge into the base.

#         Outputs
#         --------
#         - **DeepDict**: A new dictionary that is the deep merge of both.
#         """
#         result = DeepDict(dict1)
#         result.deep_update(dict2)
#         return result

#     def __add__(self, other):
#         """
#         Implements the + operator to perform a deep merge of two dictionaries.

#         Inputs
#         -------
#         - **other**: dict
#             The dictionary to merge with.

#         Outputs
#         --------
#         - **DeepDict**: A new DeepDict instance with the merged contents.
#         """
#         if not isinstance(other, dict):
#             raise TypeError("Can only add another dict or DeepDict")
#         return DeepDict.merge(self, other)

                