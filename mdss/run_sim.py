import os
import time
import copy
from datetime import date, datetime

import pandas as pd
import numpy as np
import yaml
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from mpi4py import MPI

from mdss.helpers import *
from mdss.aerostruct import run_problem as run_aerostructural

comm = MPI.COMM_WORLD

class run_sim():
    """
    Executes ADflow simulations using the `Top` class defined in [`aerostruct.py`](aerostruct.py).

    This class sets up, runs, and post-processes aerodynamic and/or aerostructural simulations based on input parameters provided via a YAML configuration file. It validates the input, manages directories, and handles outputs, including plots and summary files.

    Methods
    -------
    **run_problem()**
        Sets up and runs the OpenMDAO problem for all hierarchies, cases, and refinement levels in subprocesses.

    **run()**
        Helps to execute the simulation on either a local machine or an HPC system.

    **post_process()**
        Generates plots comparing experimental data (if available) with ADflow simulation results.

    Inputs
    ----------
    - **info_file** : str
        Path to the YAML file containing simulation configuration and information.
    """

    def __init__(self, info_file):
        # Validate the input yaml file
        check_input_yaml(info_file)
        msg = f"YAML file validation is successful"
        print_msg(msg, None, comm)

        self.info_file = info_file
        self.sim_info = load_yaml_file(self.info_file, comm)
        self.out_dir = os.path.abspath(self.sim_info['out_dir'])
        self.final_out_file = os.path.join(self.out_dir, "overall_sim_info.yaml") # Setting the overall simulation info file.
        self.subprocess_flag = 1
        

        # Create the output directory if it doesn't exist
        if not os.path.exists(self.out_dir): 
            if comm.rank == 0:
                os.makedirs(self.out_dir)
    
    ################################################################################
    # Code for running simulations
    ################################################################################   
    def run_problem(self):
        """
        Runs the aerodynamic and/or aerostructural simulations as subprocesses.

        This method iterates through all hierarchies, cases, refinement levels, and angles of attack defined in the input YAML file. Runs the simulation by calling `aerostruct.py`, and stores the results.

        Outputs
        -------
        - **A CSV file**:
            Contains results for each angle of attack at the current refinement level.
        - **A YAML file**:
            Stores simulation data for each angle of attack in the corresponding directory.
        - **A final YAML file**:
            Summarizes all simulation results across hierarchies, cases, and refinement levels.

        Notes
        -----
        This method ensures that:

        - Existing successful simulations are skipped.
        - Directories are created dynamically if they do not exist.
        - Simulation results are saved in structured output files.
        """

        # Store a copy of input YAML file in output directory
        input_yaml_file = os.path.join(self.out_dir, "input_file.yaml")
        if comm.rank == 0:
            with open(input_yaml_file, 'w') as input_yaml_handle:
                yaml.dump(self.sim_info, input_yaml_handle, sort_keys=False)
        
        sim_info_copy = copy.deepcopy(self.sim_info) # Copying to run the loop
        sim_out_info = copy.deepcopy(self.sim_info) # Copying to write the output YAML file
        start_time = time.time()
        start_wall_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for hierarchy, hierarchy_info in enumerate(sim_info_copy['hierarchies']): # loop for Hierarchy level

            for case, case_info in enumerate(hierarchy_info['cases']): # loop for cases in hierarchy
                # Assign problem type
                try:
                    problem_type = ProblemType.from_string(case_info['problem'])  # Convert string to enum
                except ValueError as e:
                    print(e)

                # Define case level outptut directory
                case_out_dir = os.path.join(self.out_dir, hierarchy_info['name'], case_info['name'])
                if not os.path.exists(case_out_dir): # Create the directory if it doesn't exist
                    if comm.rank == 0:
                        os.makedirs(case_out_dir)
                comm.Barrier()
                # Save case info yaml file in the case_out_dir to pass in subprocess
                case_info_fpath = os.path.join(case_out_dir, "case_info.yaml")
                with open(case_info_fpath, 'w') as case_info_fhandle:
                    yaml.dump(case_info, case_info_fhandle, sort_keys=False)

                for scenario, scenario_info in enumerate(case_info['scenarios']): # loop for scenarios that may present
                    
                    # Define scenario level output directory
                    scenario_out_dir = os.path.join(case_out_dir, scenario_info['name'])
                    if not os.path.exists(scenario_out_dir): # Create the directory if it doesn't exist
                        if comm.rank == 0:
                            os.makedirs(scenario_out_dir)
                    comm.Barrier()
                    # Save case info yaml file in the case_out_dir to pass in subprocess
                    scenario_info_fpath = os.path.join(scenario_out_dir, "scenario_info.yaml")
                    with open(scenario_info_fpath, 'w') as scenario_info_fhandle:
                        yaml.dump(scenario_info, scenario_info_fhandle, sort_keys=False)

                    if comm.rank == 0:
                        print(f"{'#' * 30}")
                        print(f"{'SIMULATION INFO':^30}")
                        print(f"{'#' * 30}")
                        print(f"{'Hierarchy':<20}: {hierarchy_info['name']}")
                        print(f"{'Case Name':<20}: {case_info['name']}")
                        print(f"{'Scenario':<20}: {scenario_info['name']}")
                        print(f"{'=' * 30}")
                    
                    # Extract the Angle of attacks for which the simulation has to be run
                    aoa_list = scenario_info['aoa_list']
                    aoa_csv_string = ",".join(map(str, [float(aoa) for aoa in aoa_list]))
                    scenario_sim_info = {} # Creating scenario level sim info dictionary for overall sim info file

                    for ii, mesh_file in enumerate(case_info['mesh_files']): # Loop for refinement levels

                        refinement_level = f"L{ii}"
                        AOAList = []
                        CLList = []
                        CDList = []
                        TList = []
                        FList = [] # Fail flag list

                        refinement_level_dict = {} # Creating refinement level sim info dictionary for overall sim info file
                        refinement_out_dir = os.path.join(scenario_out_dir, f"{mesh_file}")
                        if not os.path.exists(refinement_out_dir): # Create the directory if it doesn't exist
                            if comm.rank == 0:
                                os.makedirs(refinement_out_dir)

                        aero_grid_fpath = os.path.join(case_info['meshes_folder_path'], mesh_file)
                        # Add struct mesh file for aerostructural case else set it to none
                        if problem_type == ProblemType.AEROSTRUCTURAL:
                            struct_mesh_file = case_info['struct_options']['mesh_fpath']
                        else:
                            struct_mesh_file = 'none'


                        # Run subprocess
                        # Initially running all the aoa in a subprocess. However the optimal number of aoa for single subprocess should be determined and modified accordingly.
                        if self.subprocess_flag == 1:
                            run_as_subprocess(sim_info_copy, case_info_fpath, scenario_info_fpath, refinement_out_dir, aoa_csv_string, aero_grid_fpath, comm, struct_mesh_file)
                        elif self.subprocess_flag == 0:
                            run_aerostructural(case_info_fpath, scenario_info_fpath, refinement_out_dir, aoa_csv_string, aero_grid_fpath, struct_mesh_file)
                        failed_aoa_list = [] # Initiate a list to store a list of aoa failed in this refinement level
                
                        for aoa in aoa_list: # loop for angles of attack reads the info, adds additional info if needed for the output file for each aoa

                            # Date
                            current_date = date.today()
                            date_string = current_date.strftime("%Y-%m-%d")

                            aoa = float(aoa) # making sure aoa is a float
                            aoa_out_dir = os.path.join(refinement_out_dir, f"aoa_{aoa}") # aoa output directory -- Written to store in the parent directory
                            aoa_info_file = os.path.join(aoa_out_dir ,f"aoa_{aoa}.yaml") # name of the simulation info file at the aoa level directory
                            aoa_level_dict = {} # Creating aoa level sim info dictionary for overall sim info file

                            # Checking for existing sucessful simualtion info, 
                            try:
                                with open(aoa_info_file, 'r') as aoa_file: # open the simulation info file
                                    aoa_sim_info = yaml.safe_load(aoa_file)

                                fail_flag = aoa_sim_info['fail_flag'] # Read the fail flag

                                # Add Additional info to the aoa_sim_info
                                additional_aoa_sim_info = {
                                    'refinement_level': refinement_level,
                                }
                                aoa_sim_info.update(additional_aoa_sim_info)

                                if fail_flag == 0: # Refers successful simulation
                                    # Add the simulation info to list to be saved as a csv file in the refinement out directory
                                    AOAList.append(aoa_sim_info['AOA'])
                                    CLList.append(aoa_sim_info['cl'])
                                    CDList.append(aoa_sim_info['cd'])
                                    TList.append(float(aoa_sim_info['wall_time'].replace(" sec", "")))
                                    FList.append(fail_flag)

                                    # Store the basic info that is needed to be stored in refinement level dictionary
                                    aoa_level_dict = {
                                        'cl': float(aoa_sim_info['cl']),
                                        'cd': float(aoa_sim_info['cd']),
                                        'wall_time': aoa_sim_info['wall_time'],
                                        'fail_flag': int(fail_flag),
                                        'out_dir': aoa_out_dir,
                                    }
                                    refinement_level_dict[f"aoa_{aoa}"] = aoa_level_dict
                                    refinement_level_dict["failed_aoa"] = failed_aoa_list
                                
                                elif fail_flag == 1: # refers to failed simulation
                                    failed_aoa_list.append(aoa) # Add to the list of failed aoa
                                
                                # Save the aoa_out_dict as an yaml file with the updated info
                                with open(aoa_info_file, 'w') as interim_out_yaml:
                                    yaml.dump(aoa_sim_info, interim_out_yaml, sort_keys=False)

                            except:
                                failed_aoa_list.append(aoa) # Add to the list of failed aoa
                        ################################# End of AOA loop ########################################

                        # Write simulation results to a csv file
                        refinement_level_data = {
                            "Alpha": [f"{alpha:6.2f}" for alpha in AOAList],
                            "CL": [f"{cl:8.4f}" for cl in CLList],
                            "CD": [f"{cd:8.4f}" for cd in CDList],
                            "FFlag": [f"{int(FF):12f}" for FF in FList],
                            "WTime": [f"{wall_time:10.2f}" for wall_time in TList]
                        }

                        # Define the output file path
                        refinement_level_dir = os.path.dirname(aoa_out_dir)
                        ADflow_out_file = os.path.join(refinement_level_dir, "ADflow_output.csv")
                        
                        df = pd.DataFrame(refinement_level_data) # Create a panda DataFrame
                        df.to_csv(ADflow_out_file, index=False)# Write the DataFrame to a CSV file

                        # Add csv file location to the overall simulation out file
                        refinement_level_dict['csv_file'] = ADflow_out_file
                        refinement_level_dict['refinement_out_dir'] = refinement_level_dir

                        # Add refinement level dict to scenario level dict
                        scenario_sim_info[f"{refinement_level}"] = refinement_level_dict
                    ################################# End of refinement loop ########################################

                    # Add scenario level simulation to the overall simulation out file
                    scenario_out_dir = os.path.dirname(refinement_level_dir)
                    scenario_sim_info['scenario_out_dir'] = scenario_out_dir
                    sim_out_info['hierarchies'][hierarchy]['cases'][case]['scenarios'][scenario]['sim_info'] = scenario_sim_info

                    if os.path.exists(scenario_info_fpath): # Remove the scenario_info yaml file
                        if comm.rank==0:
                            os.remove(scenario_info_fpath)
                ################################# End of scenarios loop ########################################
                
                if os.path.exists(case_info_fpath): # Remove the case_info yaml file
                    if comm.rank==0:
                        os.remove(case_info_fpath)
            ################################# End of case loop ########################################
        ################################# End of hierarchy loop ########################################

        end_time = time.time()
        end_wall_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        net_run_time = end_time - start_time
        sim_out_info['overall_sim_info'] = {
            'start_time': start_wall_time,
            'end_time': end_wall_time,
            'total_wall_time': f"{net_run_time:.2f} sec"
        }

        # Store the final simulation out file.
        if os.path.exists(self.final_out_file):
            prev_sim_info = load_yaml_file(self.final_out_file, comm) # Load the previous sim_out_info
            prev_sim_info.update(sim_out_info) # Update the previous sim_out_info instead of overwriting it
            sim_out_info = prev_sim_info # Ensure sim_out_info contains the merged data

        if comm.rank == 0:
            with open(self.final_out_file, 'w') as final_out_yaml_handle:
                yaml.dump(sim_out_info, final_out_yaml_handle, sort_keys=False)
        comm.Barrier()
    
    ################################################################################
    # Code for user to run simulations
    ################################################################################
    def run(self):
        """
        Executes the simulation on either a local machine or an HPC system. 

        This method checks the simulation settings from the input YAML file. Based on the `hpc` flag, it either runs the simulation locally or generates an HPC job script for execution.

        Notes
        -----
        - For local execution (`hpc: no`), it directly calls `run_problem()`.
        - For HPC execution (`hpc: yes`), it creates a Python file and a job script, then submits the job.
        """
        sim_info_copy = copy.deepcopy(self.sim_info)
        if sim_info_copy['hpc'] == "no": # Running on a local machine
            self.run_problem()

        elif sim_info_copy['hpc'] == "yes": # Running on a HPC currently supports Great Lakes.
            submit_job_on_hpc(sim_info_copy, self.info_file, comm) # Submit job script

            
            
    ################################################################################
    # Code for Post Processing
    ################################################################################
    
    def post_process(self):
        """
        Generates plots comparing experimental data with ADflow simulation results.

        This method creates comparison plots for each scenario and refinement level. The plots include `CL` (Lift Coefficient) and `CD` (Drag Coefficient) against the angle of attack (Alpha). Experimental data, if provided, is included in the plots for validation.

        Outputs
        -------
        - *PNG plots*:
            Stored in the scenario directory for each hierarchy and case.

        Notes
        -----
        - Experimental data is optional. If not provided, only simulation results are plotted.
        - Plots are saved with clear labels and legends for easy interpretation.
        """
        sim_out_info = load_yaml_file(self.final_out_file, comm)

        for hierarchy, hierarchy_info in enumerate(sim_out_info['hierarchies']): # loop for Hierarchy level
            for case, case_info in enumerate(hierarchy_info['cases']): # loop for cases in hierarchy
                for scenario, scenario_info in enumerate(case_info['scenarios']): # loop for scenarios that may present
                    
                    # Plot setup
                    fig, axs = plt.subplots(1, 2, figsize=(14, 6))
                    fig.suptitle('Comparison between ADflow Simulation and Experimental Data')

                    # Load Experimental Data
                    try:
                        exp_data = load_csv_data(scenario_info['exp_data'], comm)
                    except:
                        msg = f"Experimental data location is not specified or the data is not readable.\nContinuing to plot without experimental data."
                        print_msg(msg, 'warning', comm)
                        exp_data = None

                    if exp_data is not None: # Only plot if data loaded successfully
                        exp_data.columns = exp_data.columns.str.strip()  # Clean column names
    
                        # Convert to numeric to avoid plotting issues
                        exp_data['Alpha'] = pd.to_numeric(exp_data['Alpha'], errors='coerce')
                        exp_data['CL'] = pd.to_numeric(exp_data['CL'], errors='coerce')
                        exp_data['CD'] = pd.to_numeric(exp_data['CD'], errors='coerce')
                        exp_data = exp_data.dropna()  # Drop rows with missing data
                        
                        axs[0].plot(exp_data['Alpha'], exp_data['CL'], label='Experimental', color='black', linestyle='--', marker='o')
                        axs[1].plot(exp_data['Alpha'], exp_data['CD'], label='Experimental', color='black', linestyle='--', marker='o')

                    num_levels = len(case_info['mesh_files'])  # Total refinement levels
                    colors = cm.viridis(np.linspace(0, 1, num_levels))  # Generate unique colors for each level
                    # Load Simulated Data
                    scenario_out_dir = scenario_info['sim_info']['scenario_out_dir']
                    sim_data = {}
                    for ii, mesh_file in enumerate(case_info['mesh_files']): # Loop for refinement levels
                        refinement_level_dir = os.path.join(scenario_out_dir, f"{mesh_file}")
                        ADflow_out_file = os.path.join(refinement_level_dir, "ADflow_output.csv")
                        sim_data = load_csv_data(ADflow_out_file, comm)
                        if sim_data is not None:  # Only plot if data loaded successfully
                            label = f"L{ii}"
                            axs[0].plot(sim_data['Alpha'], sim_data['CL'], label=label, color=colors[ii], linestyle='-', marker='s') # Plot CL vs Alpha for this refinement level
                            axs[1].plot(sim_data['Alpha'], sim_data['CD'], label=label, color=colors[ii], linestyle='-', marker='s') # Plot CD vs Alpha for this refinement level
                    
                    # Setting titles, labels, and legends
                    axs[0].set_title('$C_L$ vs Alpha')
                    axs[0].set_xlabel('Alpha (deg)')
                    axs[0].set_ylabel('$C_L$')
                    axs[0].legend()
                    axs[0].grid(True)

                    axs[1].set_title('$C_D$ vs Alpha')
                    axs[1].set_xlabel('Alpha (deg)')
                    axs[1].set_ylabel('$C_D$')
                    axs[1].legend()
                    axs[1].grid(True)

                    plt.tight_layout(rect=[0, 0, 1, 0.96])  # Adjust layout to fit title
                    plt.savefig(os.path.join(scenario_out_dir, "ADflow_Results.png"))