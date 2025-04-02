
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
