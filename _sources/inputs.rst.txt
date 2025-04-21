.. include:: _substitutions.rst

Inputs
======

The |mdss|_ package requires an `yaml
file <#yaml-configuration-file>`__ to configure and execute simulations.

YAML Configuration File
-----------------------

A YAML file is required to define the simulation parameters and organize
test cases. The YAML file structure and respective descriptions are
given below.

Input YAML file Structure
~~~~~~~~~~~~~~~~~~~~~~~~~

The YAML file organizes simulation data into a structured hierarchy,
enabling clear configuration of cases and experimental conditions. Below
is the structure used in the YAML file:

.. code-block:: yaml

   out_dir: # str, path to the output directory
   python_version: # str, path to the python env to use
   machine_type: # str, local/hpc
   nproc: # int, number of processors, required when machine_type is local
   hpc_info: # dict, required only if machine_type is hpc
     cluster: # str, name of the cluster. GL for Great Lakes
     job_name: # str, name of the job
     nodes: # int, number of nodes
     nproc: # int, total number of processors
     time: #str, time in D-H:M:S format
     account_name: # str, account name
     email_id: # str
   hierarchies: # list, List of hierarchies
   # First hierarchy
   - name: # str, name of the hierarchy
     cases: # list, list of cases in this hierarchy
     # First case in the hierarchy
     - name: # str, name of the case
       meshes_folder_path: # str, path to the floder containing the mesh files for this case
       mesh_files: # list, list of mesh file names
       - # str, name of the finest mesh
       - # str, .
       - # str, .
       - # str, name of the corasest mesh
       geometry_info: # dict, dictionary of geometry info
         chordRef: # float, reference chord length
         areaRef: # float, reference area
       aero_options: # dict, dictionary of ADflow solver parameters. For more information see aero options section
         # ......
       scenarios: # list, list of dictionaries containing scenario info
       # First experimental set in current case
       - name: # str, name of the scenario
         aoa_list: # list, list of angle of attacks(AoA) to run in with the experimental info
         Re: # float, Reynold's number 
         mach: # float, Mach number
         Temp: # float, Temperature in Kelvin scale
         exp_data: # str, path to experimental data
       
       # Second scenario in current case

       ##########################################################################
       # The following options are required only for Aerostructural problems
       ##########################################################################
       struct_options: # dict, structural options,
         isym: # int, direction of symmetry
         t: # float, Shell Thickness in m
         mesh_fpath: # str, path to the structural mesh file
         struct_properties: # dict, a dictionary containing structural properties
           # Material Properties
           rho: # float, Density in kg/m^3
           E: # float, Young's modulus in N/m^2
           nu: # float, Poisson's ratio
           kcorr: # float, Shear correction factor
           ys: # float, Yeild stress in N/m^2

         load_info: # dict, 
           g: # list, g-vector in m/s^2, the default is [0, -9.81, 0]
           inertial_load_factor: # float, times of 'g'.

         solver_options: # dict, solver options for coupling. Check solver options section for more info


     # Second case in current hierachy

   # Second hierarchy

Please note that adherence to this structure is essential; any deviation
may lead to errors when running simulations. Examples of correctly
formatted YAML files are provided in the ``examples/inputs`` folder.

These yaml script can also be used as a starting point for generating
custom YAML files.

Aero Options
~~~~~~~~~~~~

``aero_options`` is a dictionary containing options specific to the
ADflow CFD solver, allowing users to customize the solver’s behavior to
suit their simulation needs. Detailed descriptions of these parameters
and their usage can be found in the `ADflow
Documentation <https://mdolab-adflow.readthedocs-hosted.com/en/latest/options.html>`__.

If the dictionary is empty or if the default parameters are not
modified, the code will use a predefined set of default solver options.
These defaults are designed to provide a reliable baseline configuration
for running simulations effectively without requiring manual
adjustments.

Default ``aero_options`` for aerodynamic problem
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Print Options
  "printIterations": False,
  "printAllOptions": False,
  "printIntro": False,
  "printTiming": False,
  # I/O Parameters
  "outputDirectory": ".",
  "monitorvariables": ["resrho", "resturb", "cl", "cd", "yplus"],
  "writeTecplotSurfaceSolution": True,
  "solutionPrecision": "double", #  Best for restart
  "volumeVariables": ['resrho', 'mach'],
  # Physics Parameters
  "equationType": "RANS",
  "liftindex": 3,  # z is the lift direction
  # Solver Parameters
  "smoother": "DADI",
  "CFL": 0.5,
  "CFLCoarse": 0.25,
  "MGCycle": "sg",
  "MGStartLevel": -1,
  "nCyclesCoarse": 250,
  # ANK Solver Parameters
  "useANKSolver": True,
  "nSubiterTurb": 5,
  # Termination Criteria
  "L2Convergence": 1e-12,
  "L2ConvergenceCoarse": 1e-2,
  "nCycles": 75000,

Default ``aero_options`` for aerostructural problems
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Print Options
  "printIterations": False,
  "printAllOptions": False,
  "printIntro": False,
  "printTiming": False,
  # I/O Parameters
  "outputDirectory": '.', 
  "monitorvariables": ["resrho", "resturb", "cl", "cd", "yplus"],
  "writeTecplotSurfaceSolution": True,
  # Physics Parameters
  "equationType": "RANS",
  "liftindex": 3,  # z is the lift direction
  # Solver Parameters
  "smoother": "DADI",
  "CFL": 1.5,
  "CFLCoarse": 1.25,
  "MGCycle": "sg",
  "MGStartLevel": -1,
  "nCyclesCoarse": 250,
  # ANK Solver Parameters
  "useANKSolver": True,
  "nSubiterTurb": 5,
  # Termination Criteria
  "L2Convergence": 1e-12,
  "L2ConvergenceCoarse": 1e-2,
  "L2ConvergenceRel": 1e-3,
  "nCycles": 10000,
  # force integration
  "forcesAsTractions": False,

Scenarios
~~~~~~~~~

To define the problem, referred to as the **AeroProblem** (focused on
aerodynamics), flight conditions along with the name and a list of Angle
of Attacks(AoA) is required, and path to the experimental data is
optional.

Check
`mdolab-baseclasses <https://mdolab-baseclasses.readthedocs-hosted.com/en/latest/pyAero_problem.html>`__
for valid combinations flight conditions.The other properties will be
calculated automatically by |baseClasses| based on the
specified values and the governing gas laws.

Location of Mesh Files
~~~~~~~~~~~~~~~~~~~~~~

Specifying the location of the mesh files requires two inputs in every
case:

-  ``meshes_folder_path`` gets the path to the folder that contains the
   mesh files
-  ``mesh_files`` gets the list of file names, that to be run, in the
   folder specified above.

Solver Options
~~~~~~~~~~~~~~

``solver_options`` is a dictionary containing options for
``NonlinearBlockGS`` and ``LinearBlockGS`` solvers available in
``openMDAO``. If these are not provided, the default options will be
used. For more more information on these solvers visit the `openMDAO
documentation <https://openmdao.org/newdocs/versions/latest/features/building_blocks/solvers/solvers.html>`__

Default ``solver_options``
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: yaml

   "linear_solver_options": 
     "atol": 1e-08, # absolute error tolerance
     "err_on_non_converge": True, # When True, AnalysisError will be raised if not convereged
     "maxiter": 25, # maximum number of iterations
     "rtol": 1e-8, # relative error tolerance
     "use_aitken": True, # set to True to use Aitken

   "nonlinear_solver_options":
     "atol": 1e-08, # absolute error tolerance
     "err_on_non_converge": True, # When True, AnalysisError will be raised if not convereged
     "reraise_child_analysiserror": False, # When the option is true, a solver will reraise any AnalysisError that arises during subsolve; when false, it will continue solving.
     "maxiter": 25, # maximum number of iterations
     "rtol": 1e-08, # relative error tolerance
     "use_aitken": True, # set to True to use Aitken
