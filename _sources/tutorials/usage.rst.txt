.. include:: ../_substitutions.rst

Usage
=====

Run a script from examples
--------------------------

The `script <#running-simulations>`__ below runs a simulation of the NACA 0012 Airfoil, and is included in the ``examples`` folder.

**To run the above python script:**

-  Copy the examples directory to a different location (to avoid changes to your clone of the repository):

.. code:: bash

   $ cp -r <path-to-repository>/examples <path-to-examples-directory> 

-  Navigate into the directory:

.. code:: bash

   $ cd <path-to-examples-directory> 

-  Run the python script:

.. code:: bash

   $ python example.py --inputFile <path-to-input-yaml-file>

.. note:: 

   -  The script can be run in a docker container or on a local machine.
   -  If you are using a docker container, make sure to mount the examples directory to the container.
   -  If you are using a local machine, make sure to have the required dependencies installed.
   -  The script can be run in parallel by using the ``--parallel`` flag.
   -  The script can be run in batch mode by using the ``--batch`` flag.
   -  The script can be run in debug mode by using the ``--debug`` flag.

-  Do not use ``mpirun`` to run a script with |mdss|. Because, it runs simulations on subprocesses and using ``mpirun`` results in an error.
-  Example input yaml files to run on local machines are stored in ``examples/inputs/Local`` directory, and for Great Lakes HPC cluster, an example file is stored in ``examples/inputs/GL``.
-  Make sure to modify the file and file paths to absolute paths in the yaml file when running in a docker container.

Use ``examples/inputs/Local/naca0012_sinInfo.yaml`` or ``examples/inputs/GL/naca0012_sinInfo.yaml`` (for Great Lakes) to test the package with NACA0012 airfoil.

After execution, the following results are expected which are saved in
the specified output directory.

-  A copy of the input yaml file in the output directory.
-  ``overall_sim_info.yaml`` in the output directory.
-  ``ADflow_Results.png`` in each experimental level directory, that is a plot comparing :math:`C_L`, and :math:`C_D` values at all refinement levels to the experimental data(if provided).

.. image:: test_run_doc/ADflow_Results.png
   :width: 150%   
   :align: center
   :alt: Results for NACA 0012
   :scale: 80%

-  ``ADflow_output.csv`` in each refinement level directory, that is a
   file containg Angle of Attack(AoA), CL, and CD data.
-  ``aoa_<aoa>.yaml`` in aoa level directory, that contains the
   simulation information particular to that angle of attack.
-  Default ADflow outputs: A tecplot file, a CGNS surface file, and a
   CGNS volume file.

Example usage
-------------

Here are quick examples of how to different classes and functions in |mdss|:

Running Simulations
~~~~~~~~~~~~~~~~~~~

.. code:: python

   from mdss import simulation
   from mdss import post_process

   # Initialize the runner with configuration file
   sim = simulation('/path/to/input-yaml-file')

   # Run the simulation series
   sim.run()

   # Run the post-processing
   pp = post_process('/path/to/output-directory')
   pp.gen_case_plots()

Additional Information
----------------------

Grid Files
~~~~~~~~~~

Grids for NACA 0012 and Mc Donnell Dolugas 30P-30N are provided under ``examples/grids`` in the examples directory. The other grids (CRM clean, and DLR High-Lift) including 
Naca 0012 and 30P-30N can be found at `Dropbox folder <https://www.dropbox.com/scl/fo/fezdu5be849c78vze7l19/ACCsSHpLGEwCcyFEPWj2FB0?rlkey=ixbr0606y3vx5eadrs61b9cz3&st=i4evwxed&dl=0>`__.

Aero and structural grid files for the Mach Aero Wing can be downladed from `mphys repo <http://umich.edu/~mdolaboratory/repo_files/mphys/mphys_input_files.tar.gz>`__. An example input yaml file for the Mach Aero Wing is provided in ``examples/inputs/Local/mach_aero_wing.yaml``. The example yaml file is set up to run on local machines.

Experimental data
~~~~~~~~~~~~~~~~~

Experimental data for NACA 0012 and Mc Donnell Dolugas 30P-30N are provided under ``examples/exp_data`` in the examples directory. The
other dat (CRM clean, and DLR High-Lift) including Naca 0012 and 30P-30N, and their references can be found at `Dropbox
folder <https://www.dropbox.com/scl/fo/18rcs9bh0qmf19ymptrt2/AHx-xyYSXk_wGXqhvVV2yMM?rlkey=kp0vovsegpddfn78wfjiv8gbi&st=2czi5hbu&dl=0>`__.
