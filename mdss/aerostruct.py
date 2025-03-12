import os
import time
import numpy as np
import yaml
import shutil

from mphys import MPhysVariables, Multipoint
from mphys.scenarios import ScenarioAeroStructural, ScenarioAerodynamic
from mpi4py import MPI
from adflow.mphys import ADflowBuilder
from baseclasses import AeroProblem
try: # The following modules are required only for Aerostructural problems
    from tacs.mphys import TacsBuilder
    from funtofem.mphys import MeldBuilder
    from mdss.tacs_setup import tacs_setup
except:
    pass


import openmdao.api as om
from mpi4py import MPI

from mdss.helpers import *
from mdss.templates import default_aero_options_aerodynamic, default_aero_options_aerostructural, default_structural_properties, default_solver_options


comm = MPI.COMM_WORLD

class Top(Multipoint):
    """
    Sets up an OpenMDAO problem using MPhys, ADflow, and/or TACS for aerodynamic or aerostructural simulations.

    This class is designed to integrate ADflow and TACS using MPhys to perform aerodynamic or aerostructural simulations. It sets up the problem environment, manages inputs and outputs, and configures scenarios for simulation.

    Methods
    --------
    **setup()**
        Initializes and sets up the required subsystems and scenarios.

    **configure()**
        Configures the aerodynamic problem (e.g., reference area, chord, angle of attack) and connects design variables to the system.

    Inputs
    -------
    - **sim_info** : dict
        Dictionary containing geometry and configuration details for the case being analyzed. The structure of `sim_info` is as follows:
        ```python
        sim_info = {
            'problem': # str, Name of the problem Aerodynamic/Aerostructural
            'aero_options': # dict, Dictionary containing ADflow solver options
            'chordRef': # float, Reference chord length
            'areaRef': # float, Reference area
            'mach': # float, Mach Number
            'Re': # float, Reynold's Number
            'Temp': # float, Temperature in Kelvin
            
            # Add Structural Info
            'tacs_out_dir': # str, Path to the outptut directory for TACS. Can be left empty for aerodynamic problems
            'struct_mesh_fpath': # str, Path to the structural mesh file. Can be left empty for aerodynamic problems
            'structural_properties': # dict, inludes material propertires - E, ro, nu, kcorr, ys, and thickness of the shell.
            'load_info': # dict, load type - Cruise/Maneuver, gravity flag, inertial load factor for maneuver loads.
            'solver_options': # dict, solver options in openMDAO
        }
        ```

    Outputs
    --------
    None. This class directly modifies the OpenMDAO problem structure to include aerodynamic or aerostructural analysis subsystems.

    """
    def __init__(self, sim_info):
        super().__init__()
        self.sim_info = sim_info
        # Assign problem type
        try:
            self.problem_type = ProblemType.from_string(sim_info['problem'])  # Convert string to enum
        except ValueError as e:
            print(e)

    def setup(self):
        scenario = "cruise"
        if self.problem_type == ProblemType.AEROSTRUCTURAL: # TACS setup only for aerostructural scenario
            ################################################################################
            # ADflow Setup
            ################################################################################
            aero_builder = ADflowBuilder(self.sim_info['aero_options'], scenario="aerostructural")
            aero_builder.initialize(self.comm)
            aero_builder.err_on_convergence_fail = True
            self.add_subsystem("mesh_aero", aero_builder.get_mesh_coordinate_subsystem())
            ################################################################################
            # TACS Setup
            ################################################################################
            tacs_config = tacs_setup(self.sim_info['structural_properties'], self.sim_info['load_info'], self.sim_info['tacs_out_dir'])

            struct_builder = TacsBuilder(mesh_file=self.sim_info['struct_mesh_fpath'], 
                                        element_callback=tacs_config.element_callback, 
                                        coupling_loads=[MPhysVariables.Structures.Loads.AERODYNAMIC], 
                                        problem_setup=tacs_config.problem_setup)
            struct_builder.initialize(self.comm)

            self.add_subsystem("mesh_struct", struct_builder.get_mesh_coordinate_subsystem())

            ################################################################################
            # Transfer Scheme Setup
            ################################################################################
            isym = 1  # y-symmetry
            ldxfer_builder = MeldBuilder(aero_builder, struct_builder, isym=isym)
            ldxfer_builder.initialize(self.comm)

            ################################################################################
            # MPHYS Setup for AeroStructural Problem
            ################################################################################
            # ivc to keep the top level DVs
            dvs = self.add_subsystem("dvs", om.IndepVarComp(), promotes=["*"])
            init_dvs = struct_builder.get_initial_dvs()
            dvs.add_output("dv_struct", init_dvs)

            ################# Get the following inputs from the user #############################################
            nonlinear_solver = om.NonlinearBlockGS(maxiter=25, iprint=2, use_aitken=True, rtol=1e-14, atol=1e-14)
            linear_solver = om.LinearBlockGS(maxiter=25, iprint=2, use_aitken=True, rtol=1e-14, atol=1e-14)
            ######################################################################################################

            self.mphys_add_scenario(
                scenario,
                ScenarioAeroStructural(
                    aero_builder=aero_builder, struct_builder=struct_builder, ldxfer_builder=ldxfer_builder
                ),
                coupling_nonlinear_solver = nonlinear_solver,
                coupling_linear_solver = linear_solver,
            )

            self.connect(
                f"mesh_aero.{MPhysVariables.Aerodynamics.Surface.Mesh.COORDINATES}",
                f"{scenario}.{MPhysVariables.Aerodynamics.Surface.COORDINATES_INITIAL}",
            )
            self.connect(
                f"mesh_struct.{MPhysVariables.Structures.Mesh.COORDINATES}",
                f"{scenario}.{MPhysVariables.Structures.COORDINATES}",
            )

            self.connect("dv_struct", f"{scenario}.dv_struct")
        
        elif self.problem_type == ProblemType.AERODYNAMIC:
            ################################################################################
            # ADflow Setup
            ################################################################################
            aero_builder = ADflowBuilder(self.sim_info['aero_options'], scenario="aerodynamic")
            aero_builder.initialize(self.comm)
            aero_builder.err_on_convergence_fail = True
            self.add_subsystem("mesh_aero", aero_builder.get_mesh_coordinate_subsystem())

            ################################################################################
            # MPHYS setup for Aero Problem
            ################################################################################
            # ivc to keep the top level DVs
            self.add_subsystem("dvs", om.IndepVarComp(), promotes=["*"])
            self.mphys_add_scenario(scenario, ScenarioAerodynamic(aero_builder=aero_builder))
            self.connect(f"mesh_aero.{MPhysVariables.Aerodynamics.Surface.Mesh.COORDINATES}", "cruise.x_aero")
            
    def configure(self): # Set Angle of attack
        aoa = 0.0 # Set Angle of attack. Will be changed when running the problem
        ap = AeroProblem(
            name="cruise",
            # Experimental Conditions 
            mach = self.sim_info['mach'], reynolds=self.sim_info['Re'], reynoldsLength=self.sim_info['chordRef'], T=self.sim_info['Temp'],
            # Geometry Info
            alpha=aoa, 
            areaRef=self.sim_info['areaRef'],
            chordRef=self.sim_info['chordRef'],
            evalFuncs=["cl", "cd"],
        )
        ap.addDV("alpha", value=aoa, name="aoa", units="deg")

        if self.problem_type == ProblemType.AEROSTRUCTURAL:
            self.cruise.coupling.aero.mphys_set_ap(ap)
            variable_to_connect = "cruise.coupling.aero.aoa"

        elif self.problem_type == ProblemType.AERODYNAMIC:
            self.cruise.coupling.mphys_set_ap(ap)
            variable_to_connect = "cruise.coupling.aoa"
        self.cruise.aero_post.mphys_set_ap(ap)

        # define the aero DVs in the IVC
        self.dvs.add_output("aoa", val=aoa, units="deg")

        # connect to the aero for each scenario
        self.connect("aoa", [variable_to_connect, "cruise.aero_post.aoa"])

def run_problem(case_info_fpath, exp_info_fpath, ref_level_dir, aoa_csv_str, aero_grid_fpath, struct_mesh_fpath=None):
    # Extarct the required info
    case_info = load_yaml_file(case_info_fpath, comm)
    exp_info = load_yaml_file(exp_info_fpath, comm)
    aoa_list = [float(x) for x in aoa_csv_str.split(',')]

    # Assign problem type
    try:
        problem_type = ProblemType.from_string(case_info['problem'])  # Convert string to enum
    except ValueError as e:
        print(e)
    
    # Initialize the structrual info dictionaries which remains empty for aerodynamic problems
    structural_properties = {}
    laod_info = {}
    solver_options = {}

    # Assigning defaults
    # Read the respective default_aero_options
    if problem_type == ProblemType.AERODYNAMIC:
        aero_options = default_aero_options_aerodynamic.copy() # Assign default options for aerodynamic case
    elif problem_type == ProblemType.AEROSTRUCTURAL:
        solver_options = default_solver_options
        aero_options = default_aero_options_aerostructural.copy() # Assign default aero_options for aerostructural case
        structural_properties.update(default_structural_properties.copy()) # Assign default structural properties
        structural_properties.update(case_info['struct_options']['structural_properties']) # Update default with user given values
        laod_info.update(case_info['struct_options']['load_info']) # Update load info with user given values
        solver_options.update(case_info['struct_options']['solver_options']) # Update solver optiuons with user given values

    aero_options.update(case_info['aero_options']) # Update aero_options with user given values
    geometry_info = case_info['geometry_info']

    # Update Grid file
    aero_options['gridFile'] = aero_grid_fpath # Add aero_grid file path to aero_options
        
    sim_info = {
            'problem': case_info['problem'],
            'aero_options': aero_options,
            'chordRef': geometry_info['chordRef'],
            'areaRef': geometry_info['areaRef'],
            'mach': exp_info['mach'],
            'Re': exp_info['Re'],
            'Temp': exp_info['Temp'],
            
            # Add Structural Info
            'tacs_out_dir': ref_level_dir,
            'struct_mesh_fpath': struct_mesh_fpath,
            'structural_properties': structural_properties,
            'load_info': laod_info,
            'solver_options': solver_options,
        }
    
    ################################################################################
    # OpenMDAO setup
    ################################################################################
    os.environ["OPENMDAO_REPORTS"]="0" # Do this to disable report generation by OpenMDAO
    prob = om.Problem()
    prob.model = Top(sim_info)
    prob.setup() # Setup the problem
    if problem_type == ProblemType.AEROSTRUCTURAL: # Update solver options
        for key, value in solver_options['nonlinear_solver_options'].items(): 
            prob.model.cruise.coupling.nonlinear_solver.options[key] = value
        for key, value in solver_options['linear_solver_options'].items(): 
            prob.model.cruise.coupling.linear_solver.options[key] = value

    for aoa in aoa_list:
        aoa_out_dir = os.path.join(ref_level_dir, f"aoa_{aoa}") # name of the aoa output directory
        aoa_out_dir = os.path.abspath(aoa_out_dir)
        aoa_info_file = os.path.join(aoa_out_dir, f"aoa_{aoa}.yaml") # name of the simulation info file at the aoa level directory
        ################################################################################
        # Checking for existing sucessful simualtion info
        ################################################################################ 
        if os.path.exists(aoa_out_dir):
            try:
                with open(aoa_info_file, 'r') as aoa_file:
                    aoa_sim_info = yaml.safe_load(aoa_file)
                fail_flag = aoa_sim_info['fail_flag']
                if fail_flag == 0:
                    msg = f"Skipping Angle of Attack (AoA): {float(aoa):<5} | Reason: Existing successful simulation found"
                    print_msg(msg, 'notice', comm)
                    continue # Continue to next loop if there exists a successful simulation
            except:
                fail_flag = 1
        elif not os.path.exists(aoa_out_dir): # Create the directory if it doesn't exist
            if comm.rank == 0:
                os.makedirs(aoa_out_dir)
        
        ################################################################################
        # Run sim when a succesful simulation is not found
        ################################################################################
        fail_flag = 0

        # Change output directory in openMDAO instance
        if problem_type == ProblemType.AEROSTRUCTURAL:
            #print(f"{'+'*50}")
            #print(prob.model.cruise.coupling.struct.sp.options['defaults'])
            #print(prob.model.cruise.coupling.aero.options['solver'].options['outputDirectory'])
            prob.model.cruise.coupling.aero.options['solver'].options['outputDirectory'] = aoa_out_dir
            prob.model.cruise.coupling.struct.sp.setOption('outputdir', aoa_out_dir)
            #print(prob.model.cruise.coupling.aero.options['solver'].options['outputDirectory'])
            #print(prob.model.cruise.coupling.struct.sp.options['outputdir'])
            #print(f"{'+'*50}")

        elif problem_type == ProblemType.AERODYNAMIC:
            prob.model.cruise.coupling.options['solver'].options['outputDirectory'] = aoa_out_dir
        

        prob["aoa"] = float(aoa) # Set Angle of attack

        # Run the model
        aoa_start_time = time.time() # Store the start time
        try:
            prob.run_model()
            fail_flag = 0
        except:
            fail_flag = 1

        om.n2(prob, show_browser=False, outfile=os.path.join(aoa_out_dir, "mphys_n2.html"))
        
        # Manually move the '.f5' files to the respective aoa_out_dir
        if comm.rank == 0:
            for file in os.listdir(ref_level_dir):
                src_file = os.path.join(ref_level_dir, file)
                dest_file = os.path.join(aoa_out_dir, file)
                if file.endswith(".f5"):  # Identify TACS output files
                    shutil.move(src_file, dest_file)

        aoa_end_time = time.time() # Store the end time
        aoa_run_time = aoa_end_time - aoa_start_time # Compute the run time

        prob.model.list_inputs(units=True)
        prob.model.list_outputs(units=True)

        # Store a Yaml file at this level
        aoa_out_dic = {
            # 'refinement_level': refinement_level, # Decide on this later
            'AOA': float(aoa),
            'fail_flag': int(fail_flag),
            'case':case_info['name'],
            'problem': case_info['problem'],
            'aero_mesh_fpath': aero_grid_fpath,
            'exp_info': {
                'Re': exp_info['Re'],
                'mach': exp_info['mach'],
                'Temp': exp_info['Temp'],
                },
            'cl': float(prob["cruise.aero_post.cl"][0]),
            'cd': float(prob["cruise.aero_post.cd"][0]),
            'wall_time': f"{aoa_run_time:.2f} sec",
            'out_dir': aoa_out_dir,
        }
        try:
            aoa_out_dic['exp_info']['exp_data'] = exp_info['exp_data']
        except:
            aoa_out_dic['exp_info']['exp_data'] = 'Not provided'

        if problem_type == ProblemType.AEROSTRUCTURAL: # Add structural info
            struct_info_dict = {
                'struct_mesh_fpath': struct_mesh_fpath,
                'structural_properties': structural_properties,
                'load_info': laod_info,
                'solver_options': solver_options
            }
            aoa_out_dic.update(struct_info_dict)
        with open(aoa_info_file, 'w') as interim_out_yaml:
            yaml.dump(aoa_out_dic, interim_out_yaml, sort_keys=False)