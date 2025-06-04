################################################################################
# Python script to run subprocesses - DO NOT MODIFY
################################################################################
python_code_for_subprocess = """
import argparse, json
from mpi4py import MPI
from mdss import Problem

comm = MPI.COMM_WORLD
parser = argparse.ArgumentParser()
parser.add_argument("--problemInfo", type=str)
args = parser.parse_args()
problem_info = json.loads(args.problemInfo)
problem = Problem(problem_info)
problem_results = problem.run()
print("::SUBPROCESS_RESULT::" + json.dumps(problem_results) + "::SUBPROCESS_RESULT::")
"""

################################################################################
# Python script to run on a HPC - DO NOT MODIFY
################################################################################
python_code_for_hpc = """
import argparse, json
from mdss import simulation
from mdss import execute

parser = argparse.ArgumentParser()
parser.add_argument("--inputFile", type=str)
args = parser.parse_args()
sim = simulation(args.inputFile) # Input the simulation info and output dir
sim.submit_job = False
simulation_results = sim.run()
print("::FINAL_JOB_RESULT::" + json.dumps(simulation_results) + "::FINAL_JOB_RESULT::")
"""

################################################################################
# Template for Great Lakes Job script
################################################################################
gl_job_script = """#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --account={account_name}
#SBATCH --partition={partition}
#SBATCH --time={time}
#SBATCH --nodes={nodes}
#SBATCH --ntasks={nproc}
#SBATCH --ntasks-per-node={nproc_per_node}
#SBATCH --mem-per-cpu={mem_per_cpu}
#SBATCH --mail-type={mail_types}
#SBATCH --mail-user={email_id}
#SBATCH --output={out_file}

python {python_file_path} --inputFile {yaml_file_path}
"""
