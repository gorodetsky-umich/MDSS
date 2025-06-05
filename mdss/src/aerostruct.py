# Imports
import os, time, yaml, json
from mpi4py import MPI

# MDO tool imports
from mphys import MPhysVariables, Multipoint
from mphys.scenarios import ScenarioAeroStructural, ScenarioAerodynamic
from mpi4py import MPI
from adflow.mphys import ADflowBuilder
from baseclasses import AeroProblem
try: # The following modules are required only for Aerostructural problems
    from tacs.mphys import TacsBuilder
    from funtofem.mphys import MeldBuilder
    from mdss.src.tacs_config import tacs_setup

except:
    pass
import openmdao.api as om

from mdss.utils.helpers import ProblemType, load_yaml_input, print_msg, update_om_instance, get_restart_file, ensure_dict
from mdss.resources.aero_defaults import default_aero_options_aerodynamic
from mdss.resources.aerostruct_defaults import *



comm = MPI.COMM_WORLD

class Top(Multipoint):
    """
    Sets up an OpenMDAO problem using MPhys, ADflow, and/or TACS for aerodynamic or aerostructural simulations.

    This class is designed to integrate ADflow and TACS using MPhys to perform aerodynamic or aerostructural simulations. It sets up the problem environment, manages inputs and outputs, and configures scenarios for simulation.

    Parameters
    ----------
    sim_info: dict
        Dictionary containing geometry and configuration details for the case being analyzed. The structure of `sim_info` is as follows:

        .. code:: python

            sim_info = {
                'problem': # str, Name of the problem Aerodynamic/Aerostructural
                'aero_options': # dict, Dictionary containing ADflow solver options
                'chordRef': # float, Reference chord length
                'areaRef': # float, Reference area
                'mach': # float, Mach Number
                'Re': # float, Reynold's Number
                'Temp': # float, Temperature in Kelvin
                
                # Add Structural Info
                'tacs_out_dir': # str, Path to the output directory for TACS. Can be left empty for aerodynamic problems
                'struct_mesh_fpath': # str, Path to the structural mesh file. Can be left empty for aerodynamic problems
                'structural_properties': # dict, includes material properties - E, ro, nu, kcorr, ys, and thickness of the shell.
                'load_info': # dict, load type - Cruise/Maneuver, gravity flag, inertial load factor for maneuver loads.
                'solver_options': # dict, solver options in openMDAO
            }

    Returns
    -------
    None. This class directly modifies the OpenMDAO problem structure to include aerodynamic or aerostructural analysis subsystems.

    """
    def __init__(self, sim_info):
        super().__init__()
        self.sim_info = sim_info
        self.problem_type = ProblemType.from_string(sim_info['problem'])  # Convert string to enum

    def setup(self):
        """
        Initializes and sets up the required subsystems and scenarios.
        """
        if self.problem_type == ProblemType.AEROSTRUCTURAL: # TACS setup only for aerostructural scenario
            ################################################################################
            # ADflow Setup
            ################################################################################
            aero_builder = ADflowBuilder(self.sim_info['aero_options'], scenario="aerostructural")
            aero_builder.initialize(self.comm)
            aero_builder.err_on_convergence_fail = False
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
            isym = int(self.sim_info['isym'])  # y-symmetry
            ldxfer_builder = MeldBuilder(aero_builder, struct_builder, isym=isym)
            ldxfer_builder.initialize(self.comm)

            ################################################################################
            # MPHYS Setup for AeroStructural Problem
            ################################################################################
            # ivc to keep the top level DVs
            dvs = self.add_subsystem("dvs", om.IndepVarComp(), promotes=["*"])
            init_dvs = struct_builder.get_initial_dvs()
            dvs.add_output("dv_struct", init_dvs)
            nonlinear_solver = om.NonlinearBlockGS(**self.sim_info['solver_options']['nonlinear_solver_options'])
            linear_solver = om.LinearBlockGS(**self.sim_info['solver_options']['linear_solver_options'])

            self.mphys_add_scenario(
                self.sim_info['scenario_name'],
                ScenarioAeroStructural(
                    aero_builder=aero_builder, struct_builder=struct_builder, ldxfer_builder=ldxfer_builder
                ),
                coupling_nonlinear_solver = nonlinear_solver,
                coupling_linear_solver = linear_solver,
            )

            self.connect(
                f"mesh_aero.{MPhysVariables.Aerodynamics.Surface.Mesh.COORDINATES}",
                f"{self.sim_info['scenario_name']}.{MPhysVariables.Aerodynamics.Surface.COORDINATES_INITIAL}",
            )
            self.connect(
                f"mesh_struct.{MPhysVariables.Structures.Mesh.COORDINATES}",
                f"{self.sim_info['scenario_name']}.{MPhysVariables.Structures.COORDINATES}",
            )

            self.connect("dv_struct", f"{self.sim_info['scenario_name']}.dv_struct")
        
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
            self.mphys_add_scenario(self.sim_info['scenario_name'], ScenarioAerodynamic(aero_builder=aero_builder))
            self.connect(f"mesh_aero.{MPhysVariables.Aerodynamics.Surface.Mesh.COORDINATES}", f"{self.sim_info['scenario_name']}.x_aero")
            
    def configure(self): # Set Angle of attack
        """
        Configures the openMDAO problem (e.g., reference area, chord, angle of attack) and connects the MPhys variables.
        """
        super().configure() # Updates solver options to the problem
        scenario_attr = getattr(self, self.sim_info['scenario_name']) # get a common attribute for scenarios
        ################################################################################
        # Aero problem setup
        ################################################################################
        aoa = 0.0 # Set Angle of attack. Will be changed when running the problem
        ap_inputs = {
            'alpha': aoa, 
            'reynoldsLength': self.sim_info['chordRef'],
            'chordRef': self.sim_info['chordRef'],
            'areaRef': self.sim_info['areaRef'],
            'evalFuncs': ['cl', 'cd']
        }
        # Define arguments required for aero problem
        add_ap_args = {'name', 'mach', 'altitude', 'reynolds', 'reynoldsLength', 'T', 'rho', 'P', 'V'}
        # Update ap_inputs with filtered values, converting everything except 'name' to float
        ap_inputs.update({
            key: float(self.sim_info['scenario_info'][key]) if key != "name" else self.sim_info['scenario_info'][key]
            for key in add_ap_args if key in self.sim_info['scenario_info']
        })
        ap = AeroProblem(**ap_inputs)
        ap.addDV("alpha", value=aoa, name="aoa", units="deg")

        if self.problem_type == ProblemType.AEROSTRUCTURAL:
            scenario_attr.coupling.aero.mphys_set_ap(ap)
            variable_to_connect = f"{self.sim_info['scenario_name']}.coupling.aero.aoa"

        elif self.problem_type == ProblemType.AERODYNAMIC:
            scenario_attr.coupling.mphys_set_ap(ap)
            variable_to_connect = f"{self.sim_info['scenario_name']}.coupling.aoa"

        scenario_attr.aero_post.mphys_set_ap(ap)

        # define the aero DVs in the IVC
        self.dvs.add_output("aoa", val=aoa, units="deg")

        # connect to the aero for each scenario
        self.connect("aoa", [variable_to_connect, f"{self.sim_info['scenario_name']}.aero_post.aoa"])
    
class Problem:
    """
    A class to run aerodynamic or aerostructural simulations using OpenMDAO and MPhys.

    Parameters
    ----------
    problem_info: dict or str
        A dictionary or JSON string containing the problem configuration. The structure of `problem_info` is as follows:

        .. code:: python

            problem_info = {
                'case_info': { # See documentation for case_info structure}
                'scenario_info': { # See documentation for scenario_info structure}
                'ref_level_dir': str, # Directory for reference level outputs
                'aero_grid_fpath': str, # Path to the aerodynamic grid file
                'struct_mesh_fpath': str, # Optional path to the structural mesh file
                'aoa_csv_str': str, # Comma-separated string of angles of attack (e.g., '"0.0,5.0,10.0"')
            }                                                                    
    """
    
    def __init__(self, problem_info):

        problem_info = ensure_dict(problem_info)  # Ensure problem_info is a dictionary (Also converts from json)
        self.write_mdss_files = True

        # Extract the required info
        self.case_info = problem_info['case_info']
        self.scenario_info = problem_info['scenario_info']
        ref_level_dir = problem_info['ref_level_dir']
        aero_grid_fpath = problem_info['aero_grid_fpath']
        struct_mesh_fpath = problem_info.get('struct_mesh_fpath', None) # Optional structural mesh file path
        
        aoa_list = [float(x) for x in problem_info['aoa_csv_str'].strip('"').split(',')]
        self.aoa_list = aoa_list
        
        problem_type = ProblemType.from_string(self.case_info['problem'])  # Convert string to enum
        self.problem_type = problem_type

        # Initialize the structural info dictionaries which remains empty for aerodynamic problems
        structural_properties = {}
        load_info = {}
        solver_options = {}
        isym=None

        # Assigning defaults
        # Read the respective default_aero_options
        if problem_type == ProblemType.AERODYNAMIC:
            aero_options = default_aero_options_aerodynamic.copy() # Assign default options for aerodynamic case
        elif problem_type == ProblemType.AEROSTRUCTURAL:
            isym = self.case_info['struct_options']['isym']
            solver_options = default_solver_options
            aero_options = default_aero_options_aerostructural.copy() # Assign default aero_options for aerostructural case
            structural_properties.update(default_struct_properties.copy()) # Assign default structural properties
            load_info = default_load_info.copy()
            structural_properties.update({'t': self.case_info['struct_options']['t']}) # Update thickness with user given values
            # Update default values with user given data 
            struct_options = self.case_info.get('struct_options', {})
            structural_properties.update(struct_options.get('properties', {}))
            load_info.update(struct_options.get('load_info', {}))
            solver_options_updt = struct_options.get('solver_options', {})
            solver_options['linear_solver_options'].update(solver_options_updt.get('linear_solver_options', {}))
            solver_options['nonlinear_solver_options'].update(solver_options_updt.get('nonlinear_solver_options', {}))

        geometry_info = self.case_info['geometry_info']

        # Update aero_options file
        aero_options.update(self.case_info.get('aero_options', {}))
        aero_options['gridFile'] = aero_grid_fpath # Add aero_grid file path to aero_options
        
        # Update restart angle if provided
        if self.case_info.get('restart_angle', None) is not None:
            restart_angle = float(self.case_info['restart_angle'])
            restart_angle_dir = os.path.join(ref_level_dir, f"aoa_{restart_angle}")
            restart_mesh_file = get_restart_file(restart_angle_dir)
            if restart_mesh_file is not None:
                aero_options['restartFile'] = restart_mesh_file  # Update the restart file in the aero_options
        sim_info = {
                'aoa_list': aoa_list,
                'ref_level_dir': ref_level_dir,
                'problem': self.case_info['problem'],
                'scenario_name': self.scenario_info['name'],
                'aero_options': aero_options,
                'chordRef': geometry_info['chordRef'],
                'areaRef': geometry_info['areaRef'],
                'scenario_info': self.scenario_info,
                
                # Add Structural Info
                'isym': isym,
                'tacs_out_dir': ref_level_dir,
                'struct_mesh_fpath': struct_mesh_fpath,
                'structural_properties': structural_properties,
                'load_info': load_info,
                'solver_options': solver_options,
            }
        ################################################################################
        # OpenMDAO setup
        ################################################################################
        os.environ["OPENMDAO_REPORTS"]="0" # Do this to disable report generation by OpenMDAO
        prob = om.Problem()
        prob.model = Top(sim_info)
        prob.setup() # Setup the problem

        self.prob = prob
        self.sim_info = sim_info

    def run(self):
        """
        Runs the OpenMDAO problem for each angle of attack specified in ``problem_info``.

        Returns
        -------
        problem_results: dict
            A dictionary containing the results of the problem for each angle of attack.

        """
        problem_results = {} # Dictionary to store results of the problem
        for aoa in self.aoa_list:
            aoa_key = f"aoa_{aoa}"
            self.prob["aoa"] = float(aoa) # Set Angle of attack
            aoa_out_dir = os.path.join(self.sim_info.get('ref_level_dir'), f"aoa_{aoa}") # name of the aoa output directory
            aoa_out_dir = os.path.abspath(aoa_out_dir)
            aoa_info_file = os.path.join(aoa_out_dir, f"aoa_{aoa}.yaml") # name of the simulation info file at the aoa level directory
            # Update options specific to this aoa
            prob_updt = update_om_instance(self.prob, self.sim_info['scenario_name'], self.sim_info['problem'])
            prob_updt.outdir(aoa_out_dir)
            
            ################################################################################
            # Checking for existing successful simulation info
            ################################################################################ 
            if os.path.exists(aoa_info_file):
                with open(aoa_info_file, 'r') as aoa_file:
                    aoa_sim_info = yaml.safe_load(aoa_file)
                fail_flag = aoa_sim_info['fail_flag']
                if fail_flag == 0:
                    msg = f"Skipping Angle of Attack (AoA): {float(aoa):<5} | Reason: Existing successful simulation found"
                    print_msg(msg, 'notice', comm)
                    continue # Continue to next loop if there exists a successful simulation
            elif not os.path.exists(aoa_out_dir): # Create the directory if it doesn't exist
                if comm.rank == 0:
                    os.makedirs(aoa_out_dir)
            ################################################################################
            # Run sim when a successful simulation is not found
            ################################################################################
            fail_flag = 0
            # Run the model
            aoa_start_time = time.time() # Store the start time
            try:
                self.prob.run_model()
                fail_flag = 0
            except:
                fail_flag = 1

            om.n2(self.prob, show_browser=False, outfile=os.path.join(aoa_out_dir, "mphys_n2.html")) # Store n2 diagram in the output_directory

            aoa_end_time = time.time() # Store the end time
            aoa_run_time = aoa_end_time - aoa_start_time # Compute the run time

            self.prob.model.list_inputs(units=True)
            self.prob.model.list_outputs(units=True)

            if fail_flag == 0:
                problem_results[aoa_key] = {
                    'cl': self.prob[f"{self.sim_info['scenario_name']}.aero_post.cl"][0],
                    'cd': self.prob[f"{self.sim_info['scenario_name']}.aero_post.cd"][0],
                }

            if  not self.write_mdss_files:
                continue # Skip writing mdss files if write_mdss_files is False

            # Store a Yaml file at this level
            aoa_out_dic = {
                # 'refinement_level': refinement_level, # Decide on this later
                'AOA': float(aoa),
                'out_dir': aoa_out_dir,
                'fail_flag': int(fail_flag),
                'case': self.case_info['name'],
                'problem': self.case_info['problem'],
                'aero_mesh_fpath': self.sim_info.get('aero_options', {}).get('gridFile', None),
                'scenario_info': self.scenario_info,
                'cl': float(self.prob[f"{self.sim_info['scenario_name']}.aero_post.cl"][0]),
                'cd': float(self.prob[f"{self.sim_info['scenario_name']}.aero_post.cd"][0]),
                'wall_time': f"{aoa_run_time:.2f} sec",
                'aero_options': self.sim_info['aero_options'],
            }
            try:
                aoa_out_dic['scenario_info']['exp_data'] = self.scenario_info['exp_data']
            except:
                aoa_out_dic['scenario_info']['exp_data'] = 'Not provided'

            if self.problem_type == ProblemType.AEROSTRUCTURAL: # Add structural info
                struct_info_dict = {
                    'struct_mesh_fpath': self.sim_info['struct_mesh_fpath'],
                    'structural_properties': self.sim_info['structural_properties'],
                    'load_info': self.sim_info['load_info'],
                    'solver_options': self.sim_info['solver_options'],
                }
                aoa_out_dic.update(struct_info_dict)
            with open(aoa_info_file, 'w') as interim_out_yaml:
                yaml.dump(aoa_out_dic, interim_out_yaml, sort_keys=False)
        
        return problem_results