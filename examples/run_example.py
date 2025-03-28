import argparse
from mdss.run_sim import run_sim

parser = argparse.ArgumentParser()
parser.add_argument("--inputFile", type=str, default='inputs/naca0012_simInfo.yaml')
args = parser.parse_args()

sim = run_sim(args.inputFile) # Input the simulation info and output dir

sim.run() # Run the simulation