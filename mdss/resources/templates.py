################################################################################
# Python script to run subprocesses - DO NOT MODIFY
################################################################################
python_code_for_subprocess = """
import argparse
from mdss import Problem

parser = argparse.ArgumentParser()
parser.add_argument("--caseInfoFile", type=str)
parser.add_argument("--scenarioInfoFile", type=str)
parser.add_argument("--refLevelDir", type=str)
parser.add_argument("--aoaList", type=str)
parser.add_argument("--aeroGrid", type=str)
parser.add_argument("--structMesh", type=str)

args = parser.parse_args()

problem = Problem(args.caseInfoFile, args.scenarioInfoFile, args.refLevelDir, args.aoaList, args.aeroGrid, args.structMesh)
problem.run()
"""

################################################################################
# Python script to run on a HPC - DO NOT MODIFY
################################################################################
python_code_for_hpc = """
import argparse
from mdss import simulation
from mdss import execute

parser = argparse.ArgumentParser()
parser.add_argument("--inputFile", type=str)
args = parser.parse_args()
sim = simulation(args.inputFile) # Input the simulation info and output dir
execute(sim) # Run the simulation
"""

################################################################################
# Template for Greatlakes Job script
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
