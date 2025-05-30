"""
Helper functions for the "main.py" file.
Helps run simulations and manages output files.
"""

# Imports
import os, yaml, copy, subprocess, shutil, time
from datetime import datetime
import pandas as pd
from mpi4py import MPI

# Module imports
from mdss.utils.helpers import ProblemType, MachineType, make_dir, print_msg, load_yaml_input, deep_update, load_csv_data
from mdss.resources.templates import gl_job_script, python_code_for_hpc, python_code_for_subprocess
try:
    from mdss.src.aerostruct import Problem
    MODULES_NOT_FOUND = False
except:
    MODULES_NOT_FOUND = True

comm = MPI.COMM_WORLD

################################################################################
# Code for running simulations
################################################################################   
def execute(simulation):
    """
    Runs the aerodynamic and/or aerostructural simulations as subprocesses.

    This method iterates through all hierarchies, cases, refinement levels, and angles of attack defined in the input YAML file. Runs the simulation by calling `aerostruct.py`, and stores the results.
    
    Parameters
    ----------
    simulation: mdss.src.main.simulation
        Simulation class of MDSS

    Returns
    -------
    A CSV file:
        Contains results for each angle of attack at the current refinement level.
    A YAML file:
        Stores simulation data for each angle of attack in the corresponding directory.
    A final YAML file:
        Summarizes all simulation results across hierarchies, cases, and refinement levels.

    Notes
    -----
    This method ensures that:

    - Existing successful simulations are skipped.
    - Directories are created dynamically if they do not exist.
    - Simulation results are saved in structured output files.
    """
    if MODULES_NOT_FOUND is True and simulation.subprocess_flag is False:
        msg = f"""Required module are not present in the current environment. Cannot run without subprocess.
        Turn on the subprocess flag and specify the eligible python environment or install the required packages"""
        print_msg(msg, 'error', comm)
        raise ModuleNotFoundError()

    # Store a copy of input YAML file in output directory
    input_yaml_file = os.path.join(simulation.out_dir, "input_file.yaml")
    if comm.rank == 0:
        with open(input_yaml_file, 'w') as input_yaml_handle:
            yaml.dump(simulation.sim_info, input_yaml_handle, sort_keys=False)
    
    sim_info_copy = copy.deepcopy(simulation.sim_info) # Copying to run the loop
    sim_out_info = copy.deepcopy(simulation.sim_info) # Copying to write the output YAML file
    start_time = time.time()
    start_wall_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for hierarchy, hierarchy_info in enumerate(sim_info_copy['hierarchies']): # loop for Hierarchy level

        for case, case_info in enumerate(hierarchy_info['cases']): # loop for cases in hierarchy
            # Assign problem type
            problem_type = ProblemType.from_string(case_info['problem'])  # Convert string to enum

            # Define case level output directory
            case_out_dir = os.path.join(simulation.out_dir, hierarchy_info['name'], case_info['name'])
            make_dir(case_out_dir, comm)
            comm.Barrier()
            # Save case info yaml file in the case_out_dir to pass in subprocess
            case_info_fpath = os.path.join(case_out_dir, "case_info.yaml")
            with open(case_info_fpath, 'w') as case_info_fhandle:
                yaml.dump(case_info, case_info_fhandle, sort_keys=False)

            for scenario, scenario_info in enumerate(case_info['scenarios']): # loop for scenarios that may present
                
                # Define scenario level output directory
                scenario_out_dir = os.path.join(case_out_dir, scenario_info['name'])
                make_dir(scenario_out_dir, comm)
                comm.Barrier()
                # Save case info yaml file in the case_out_dir to pass in subprocess
                scenario_info_fpath = os.path.join(scenario_out_dir, "scenario_info.yaml")
                with open(scenario_info_fpath, 'w') as scenario_info_fhandle:
                    yaml.dump(scenario_info, scenario_info_fhandle, sort_keys=False)
                
                # Extract the Angle of attacks for which the simulation has to be run
                aoa_list = scenario_info['aoa_list']
                scenario_sim_info = {} # Creating scenario level sim info dictionary for overall sim info file
                scenario_sim_info['scenario_out_dir'] = scenario_out_dir

                for ii, mesh_file in enumerate(case_info['mesh_files']): # Loop for refinement levels
                    # Print simulation info message
                    msg = f"{'Hierarchy':<20}: {hierarchy_info['name']}\n{'Case Name':<20}: {case_info['name']}\n{'Scenario':<20}: {scenario_info['name']}\n{'Aero Mesh File':<20}: {mesh_file}"
                    print_msg(msg, f"{'SIMULATION INFO':^30}", comm)
                    AOAList = []
                    CLList = []
                    CDList = []
                    TList = []
                    FList = [] # Fail flag list
                    failed_aoa_list = [] # List to store the failed aoa

                    refinement_level_dict = {} # Creating refinement level sim info dictionary for overall sim info file
                    refinement_out_dir = os.path.join(scenario_out_dir, f"{mesh_file}")
                    make_dir(refinement_out_dir, comm)
                    refinement_level_csv_out_file = os.path.join(refinement_out_dir, f"{mesh_file}_output.csv")
                    aero_grid_fpath = os.path.join(case_info['meshes_folder_path'], mesh_file)
                    # Add struct mesh file for aerostructural case else set it to none
                    if problem_type == ProblemType.AEROSTRUCTURAL:
                        struct_mesh_file = case_info['struct_options']['mesh_fpath']
                    else:
                        struct_mesh_file = 'none'

                    # Loop to check for existing successful simulations
                    filtered_aoa_list = aoa_list.copy() # Copying the aoa_list to filter out the failed aoa later
                    skipped_aoa_list = [] # List to store the skipped aoa due to existing successful simulation
                    for aoa in aoa_list:
                        aoa = float(aoa) # making sure aoa is a float
                        aoa_out_dir = os.path.join(refinement_out_dir, f"aoa_{aoa}") # aoa output directory -- Written to store in the parent directory
                        aoa_info_file = os.path.join(aoa_out_dir ,f"aoa_{aoa}.yaml") # name of the simulation info file at the aoa level directory
                        # Checking for existing successful simulation info, 
                        try:
                            with open(aoa_info_file, 'r') as aoa_file: # open the simulation info file
                                aoa_sim_info = yaml.safe_load(aoa_file)

                            fail_flag = aoa_sim_info['fail_flag'] # Read the fail flag

                            if fail_flag == 0: # Refers successful simulation and makes sure only the successful simulations are added to the csv file.
                                filtered_aoa_list.remove(aoa) # Remove the aoa from the filtered aoa list
                                skipped_aoa_list.append(aoa) # Add the aoa to the skipped aoa list
                        except:
                            continue
                    
                    filtered_aoa_csv_string = '"' + ",".join(map(str, [float(aoa) for aoa in filtered_aoa_list])) + '"' # Convert the filtered aoa list to a csv string
                    skipped_aoa_csv_string = '"' + ",".join(map(str, [float(aoa) for aoa in skipped_aoa_list])) + '"' # Convert the skipped aoa list to a csv string
                    if len(skipped_aoa_list) != 0: # If no aoa is left to run, then skip the simulation
                        msg = f"Skipping the following AoA: {skipped_aoa_csv_string}\nReason: Existing successful simulation found"
                        print_msg(msg, 'notice', comm)
                    
                    if len(filtered_aoa_list) != 0: # If no aoa is left to run, then skip the simulation
                        # Initially running all the aoa in a subprocess. However the optimal number of aoa for single subprocess should be determined and modified accordingly.
                        other_sim_info = {key: value for key, value in sim_info_copy.items() if key != 'hierarchies'} # To pass just the sim_info without hierarchies
                        if simulation.subprocess_flag is True:
                            run_as_subprocess(other_sim_info, case_info_fpath, scenario_info_fpath, refinement_out_dir, filtered_aoa_csv_string, aero_grid_fpath, struct_mesh_file,  comm, simulation.record_subprocess)
                        elif simulation.subprocess_flag is False:
                            problem = Problem(case_info_fpath, scenario_info_fpath, refinement_out_dir, filtered_aoa_csv_string, aero_grid_fpath, struct_mesh_file)
                            problem.run()
            
                    for aoa in aoa_list: # loop for angles of attack reads the info, adds additional info if needed for the output file for each aoa
                        aoa = float(aoa) # making sure aoa is a float
                        aoa_out_dir = os.path.join(refinement_out_dir, f"aoa_{aoa}") # aoa output directory -- Written to store in the parent directory
                        aoa_info_file = os.path.join(aoa_out_dir ,f"aoa_{aoa}.yaml") # name of the simulation info file at the aoa level directory
                        aoa_level_dict = {} # Creating aoa level sim info dictionary for overall sim info file

                        # Checking for existing successful simulation info, 
                        try:
                            with open(aoa_info_file, 'r') as aoa_file: # open the simulation info file
                                aoa_sim_info = yaml.safe_load(aoa_file)

                            fail_flag = aoa_sim_info['fail_flag'] # Read the fail flag

                            if fail_flag == 0: # Refers successful simulation and makes sure only the successful simulations are added to the csv file.
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
                            else: # If the simulation failed, then add the aoa to the failed aoa list
                                if aoa not in failed_aoa_list:
                                    failed_aoa_list.append(aoa)
                            # Save the aoa_out_dict as an yaml file with the updated info
                            with open(aoa_info_file, 'w') as interim_out_yaml:
                                yaml.dump(aoa_sim_info, interim_out_yaml, sort_keys=False)
                        except:
                            if aoa not in failed_aoa_list: # If aoa is not in the failed aoa list, then add it to the failed aoa list
                                failed_aoa_list.append(aoa) # Add to the list of failed aoa
                    ################################# End of AOA loop ########################################
                    refinement_level_dict["failed_aoa"] = failed_aoa_list
                    # Write simulation results to a csv file
                    refinement_level_data = {
                        "Alpha": [f"{alpha:6.2f}" for alpha in AOAList],
                        "CL": [f"{cl:8.4f}" for cl in CLList],
                        "CD": [f"{cd:8.4f}" for cd in CDList],
                        "FFlag": [f"{int(FF):12f}" for FF in FList],
                        "WTime": [f"{wall_time:10.2f}" for wall_time in TList]
                    }
                    
                    df_new = pd.DataFrame(refinement_level_data) # Create a panda DataFrame
                    # If the file exists, load existing data and append new data
                    if os.path.exists(refinement_level_csv_out_file):
                        df_existing = load_csv_data(refinement_level_csv_out_file, comm)
                        df_combined = pd.concat([df for df in [df_existing, df_new] if df is not None], ignore_index=True) 
                    else:
                        df_combined = df_new
                    # Ensure Alpha column is float for sorting and deduplication
                    df_combined['Alpha'] = pd.to_numeric(df_combined['Alpha'], errors='coerce')
                    df_combined.dropna(subset=['Alpha'], inplace=True)
                    df_combined.drop_duplicates(subset='Alpha', keep='last', inplace=True)
                    df_combined.sort_values(by='Alpha', inplace=True)
                    df_combined.to_csv(refinement_level_csv_out_file, index=False)
                    
                    # Add csv file location to the overall simulation out file
                    refinement_level_dict['csv_file'] = refinement_level_csv_out_file
                    refinement_level_dict['refinement_out_dir'] = refinement_out_dir

                    # Add refinement level dict to scenario level dict
                    scenario_sim_info[f"{mesh_file}"] = refinement_level_dict
                ################################# End of refinement loop ########################################

                # Add scenario level simulation to the overall simulation out file
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
    if os.path.exists(simulation.final_out_file):
        prev_sim_info,_ = load_yaml_input(simulation.final_out_file, comm) # Load the previous sim_out_info
        deep_update(prev_sim_info, sim_out_info)  # Updates old sim data with the new sim data.
        final_sim_out_info = prev_sim_info
    else:
        final_sim_out_info = sim_out_info
    if comm.rank == 0:
        with open(simulation.final_out_file, 'w') as final_out_yaml_handle:
            yaml.dump(final_sim_out_info, final_out_yaml_handle, sort_keys=False)
    comm.Barrier()

################################################################################
# Code for generating and submitting job script on HPC
################################################################################   
def submit_job_on_hpc(sim_info, yaml_file_path, wait_for_job, comm):
    """
    Generates and submits job script on an HPC cluster.

    This function reads a slurm job script template, updates it with specific HPC parameters and file paths, saves the customized script to the output directory, and submits the job on the HPC cluster.

    Parameters
    ----------
    sim_info: dict
        Dictionary containing simulation details details.
    yaml_file_path: str
        Path to the YAML file containing simulation information.
    comm: MPI communicator  
        An MPI communicator object to handle parallelism.

    Notes
    -----
    - Supports customization for the GL cluster with Slurm job scheduling.
    - Uses regex to update the job script with provided parameters.
    - Ensures that the correct Python and YAML file paths are embedded in the job script.
    """
    out_dir = os.path.abspath(sim_info['out_dir'])
    hpc_info = sim_info['hpc_info'] # Extract HPC info
    python_fname = os.path.join(out_dir, "run_sim.py") # Python script to be run on on HPC
    out_file = os.path.join(out_dir, f"{hpc_info['job_name']}_%j.txt")

    if hpc_info['cluster'] == 'GL':
        # Fill in the template of the job script(can be found in `templates.py`) with values from hpc_info, provided by the user
        job_script = gl_job_script.format(
            job_name=hpc_info.get('job_name'),
            account_name=hpc_info.get('account_name'),
            partition=hpc_info.get('partition'),
            time=hpc_info.get('time', '1:00:00'),
            nodes=hpc_info.get('nodes'),
            nproc=hpc_info.get('nproc'),
            nproc_per_node=hpc_info.get('nproc_per_node'),
            mem_per_cpu=hpc_info.get('mem_per_cpu', '1000m'),
            mail_types=hpc_info.get('mail_types', 'NONE'),
            email_id=hpc_info.get('email_id', 'NONE'),
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
            
            subprocess_out = subprocess.run(["sbatch", job_script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) # Subprocess to submit the job script on Great Lakes
            job_id = subprocess_out.stdout.strip().split()[-1]
            print_msg(f"Job {job_id} submitted.", "notice", comm)

            if wait_for_job:
                while True:
                    check_cmd = ["squeue", "--job", job_id]
                    result = subprocess.run(check_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    if job_id not in result.stdout:
                        print_msg(f"Job {job_id} completed.", 'notice', comm)
                        break
                    time.sleep(10)  # Check every 10 seconds
        return job_id
    
################################################################################
# Helper Functions for running the simulations as subprocesses
################################################################################
def run_as_subprocess(sim_info, case_info_fpath, scenario_info_fpath, ref_out_dir, aoa_csv_string, aero_grid_fpath, struct_mesh_fpath, comm, record_flag=False):
    """
    Executes a set of Angles of Attack using mpirun for local machine and srun for HPC(Great Lakes).

    Parameters
    -----------
    sim_info: dict  
        Dictionary containing simulation details, such as output directory, job name, and nproc.
    case_info_fpath: str  
        Path to the case info yaml file
    scenario_info_fpath: str  
        Path to the scenario info yaml file
    ref_out_dir: str  
        Path to the refinement level directory
    aoa_csv_string: str 
        A list of angles of attack, in the form of csv string, that to be simulated in this subprocess
    aero_grid_fpath: 
        Path to the aero grid file that to be used for this simulation.
    struct_mesh_fpath: str
        Path to the structural mesh file that to be used. Pass str(None) when running aero problem.
    comm: MPI communicator  
        An MPI communicator object to handle parallelism.
    record_flag: bool=False, Optional
        Optional flag, stores output of the subprocess in a text file.

    Notes
    -----
    - The function ensures the proper setup of the simulation environment for the given angle of attack.
    - The generated Python script and YAML input file are specific to each simulation run.
    - Captures and displays `stdout` and `stderr` from the subprocess for troubleshooting.
    """
    out_dir = os.path.abspath(sim_info['out_dir'])
    python_fname = os.path.join(out_dir, "script_for_subprocess.py")
    machine_type = MachineType.from_string(sim_info['machine_type'])
    subprocess_out_file = os.path.join(ref_out_dir, "subprocess_out.txt")
    shell = False

    if not os.path.exists(python_fname): # Saves the python script, that is used to run subprocess in the output directory, if the file do not exist already.
        if comm.rank==0:
            with open(python_fname, "w") as file: # Open the file in write mode
                file.write(python_code_for_subprocess)

    env = os.environ.copy()
    
    python_version = sim_info.get('python_version', 'python') # Update python with user defined version or defaults to current python version
    if shutil.which(python_version) is None: # Check if the python executable exists
        python_version = 'python'
        print_msg(f"{python_version} not found! Falling back to default 'python'.", 'warning', comm)
    if comm.rank==0:
        print_msg(f"Starting subprocess for the following aoa: {aoa_csv_string}", "notice", comm)
        if machine_type==MachineType.LOCAL:
            nproc = sim_info['nproc']
            run_cmd = ['mpirun', '-np', str(nproc), python_version]
            
        elif machine_type==MachineType.HPC:
            run_cmd = ['srun', python_version]
        run_cmd.extend([python_fname, '--caseInfoFile', case_info_fpath, '--scenarioInfoFile', scenario_info_fpath, 
                '--refLevelDir', ref_out_dir, '--aoaList', aoa_csv_string, '--aeroGrid', aero_grid_fpath, '--structMesh', struct_mesh_fpath])

        with open(subprocess_out_file, "w") as outfile:
            p = subprocess.Popen(run_cmd, 
                env=env,
                stdout=subprocess.PIPE,  # Capture standard output
                stderr=subprocess.PIPE,  # Capture standard error
                text=True,  # Ensure output is in text format, not bytes
                )
            
            for line in p.stdout:
                print(line, end='')        # Optional: real-time terminal output
                if record_flag is True:
                    outfile.write(line)
                    outfile.flush()

            p.wait() # Wait for subprocess to end
        
        _, stderr = p.communicate()
        if stderr:
            print_msg(f"{stderr}", 'subprocess error/warning', comm)
        print_msg(f"Subprocess completed", "notice", comm)