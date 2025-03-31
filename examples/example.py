import argparse
from mdss import simulation

parser = argparse.ArgumentParser()
parser.add_argument("--inputFile", type=str, default='/home/sanjan/PhD/mdss/examples/inputs/Local/naca0012_simInfo.yaml')
args = parser.parse_args()

sim = simulation(args.inputFile) # Input the simulation info and output dir

sim.run() # Run the simulation