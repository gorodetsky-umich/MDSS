import argparse
from mdss import simulation
from mdss import post_process

parser = argparse.ArgumentParser()
parser.add_argument("--runType", type=str, default='simulation')
parser.add_argument("--inputFile", type=str, default='./inputs/Local/naca0012_simInfo.yaml')
parser.add_argument("--outputDir", type=str, default='./output')
args = parser.parse_args()

if args.runType == 'simulation':
    sim = simulation(args.inputFile) # Input the simulation info and output dir
    sim.run() # Run the simulation
elif args.runType == 'postProcess':
    pp = post_process(args.outputDir) # Input the output dir
    pp.gen_case_plots()