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

.. literalinclude:: input_template.yaml
   :language: yaml
   :caption: Example YAML file

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
  "solutionPrecision": "double",                                      #  Best for restart
  "volumeVariables": ['resrho', 'mach'],
  # Physics Parameters
  "equationType": "RANS",
  "liftindex": 3,                                                     # z is the lift direction
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
  "liftindex": 3,                                                   # z is the lift direction
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
     "atol": 1e-08,                         # absolute error tolerance
     "err_on_non_converge": True,           # When True, AnalysisError will be raised if not converged
     "maxiter": 25,                         # maximum number of iterations
     "rtol": 1e-8,                          # relative error tolerance
     "use_aitken": True,                    # set to True to use Aitken

   "nonlinear_solver_options":
     "atol": 1e-08,                         # absolute error tolerance
     "err_on_non_converge": True,           # When True, AnalysisError will be raised if not converged
     "reraise_child_analysiserror": False,  # When the option is true, a solver will raise any AnalysisError that arises during sub-solve; when false, it will continue solving.
     "maxiter": 25,                         # maximum number of iterations
     "rtol": 1e-08,                         # relative error tolerance
     "use_aitken": True,                    # set to True to use Aitken
