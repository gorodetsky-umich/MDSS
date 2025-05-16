.. include:: _substitutions.rst

Installation and Dependencies
=============================

Dependencies
------------

Core Framework Dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The framework requires tools developed by NASA (|OpenMDAO|_ and |MPhys_wv|_) and
the MDO Lab (MACH-Aero framework). The
`MACH-Aero <https://mdolab-mach-aero.readthedocs-hosted.com/en/latest/index.html>`__
framework houses all the core packages needed to run CFD simulations.
Below is the list of software required:

- |OpenMDAO|_
- |MPhys|_
- |baseClasses|_
- |IDWarp|_
- |ADflow|_
- |TACS|_ (Required for aerostructural simulations)
- |funtofem|_ (Required for aerostructural simulations)


These software packages may have additional third-party dependencies
like PETSc and OpenMPI. A detailed guide on the additional dependencies
required is available
`here <https://mdolab-mach-aero.readthedocs-hosted.com/en/latest/installInstructions/installFromScratch.html>`__.

Python Libraries
~~~~~~~~~~~~~~~~

The following Python libraries are also required:

-  ``numpy>=1.21``
-  ``scipy>=1.7``
-  ``mpi4py>=3.1.4``
-  ``petsc4py``
-  ``pyyaml``
-  ``matplotlib``
-  ``pandas``
-  ``pydantic``
-  ``niceplots``

--------------

Getting Started
---------------

To begin using this framework, follow these steps:

1. | **Create a Directory**
   | Set up a directory on your machine where you want to store this
     framework along with the necessary software packages.

   .. code-block:: bash

      $ mkdir <directory-path> 
      $ cd <directory-path>

2. | **Install Dependencies**
   | Follow the `Installation of
     Dependencies <#installation-of-dependencies>`__ section to ensure
     all required dependencies are installed on your system.

3. | **Install the Package**
   | Complete the setup by following the steps outlined in the `Package
     Installation <#package-installation>`__ section.

By completing these steps, you’ll have the framework ready for use.

Installation of Dependencies
----------------------------

There are two types of installation methods available - from scratch and
through Docker. If you are on a local machine, we recommend using Docker
as it is the easiest option. If you are on an HPC machine, only the
scratch installation method is available. Singularity support will be
added later. Please follow the appropriate link.

-  `Local machine (Docker) <#using-docker-recommended>`__
-  `Local machine (Scratch) <#from-scratch>`__
-  `HPC - Great Lakes (Singularity) <#singularity>`__
-  `HPC - Great Lakes (Scratch) <#scratch>`__

Local machine
~~~~~~~~~~~~~

Using Docker (Recommended)
^^^^^^^^^^^^^^^^^^^^^^^^^^

Docker is highly recommended for ease of installation:

1. Setup Docker: If you do not have Docker installed in your system,
   follow the `Docker Guide <https://docs.docker.com/>`__ to set it up.

2. Pull a Docker image: Official images for GCC and INTEL compilers are
   available
   `here <https://mdolab-mach-aero.readthedocs-hosted.com/en/latest/installInstructions/dockerInstructions.html>`__.
   Follow the instructions in the link to pull an image compatible to
   your systems’ architecture.

3. Initialize and start a container, follow the instructions mentioned
   `here <https://mdolab-mach-aero.readthedocs-hosted.com/en/latest/installInstructions/dockerInstructions.html#initialize-docker-container>`__
   to initialize and start a container. Mount the directory
   ``<directory-path>`` into the folder mentioned in
   `here <https://mdolab-mach-aero.readthedocs-hosted.com/en/latest/installInstructions/dockerInstructions.html#initialize-docker-container>`__.

4. Inside the container, navigate to the ``mount`` directory and clone
   this repository following the instructions in the `Package
   Installation <#package-installation>`__ section.

5. Run the testcase (TBD)

.. note::
   
   If you are referencing any paths inside the container, they must
   be with respect to the container’s folder architecture, not your host
   machine.

From Scratch
^^^^^^^^^^^^

To manually install all dependencies, we will refer to the instructions
found in the `Scratch Installation
Guide <https://mdolab-mach-aero.readthedocs-hosted.com/en/latest/installInstructions/installFromScratch.html>`__.

(Sanjan needs to fix the local install bash file, unable to identify
issue with petsc. Will do soon.)

HPC Systems (Great Lakes)
~~~~~~~~~~~~~~~~~~~~~~~~~

Singularity
^^^^^^^^^^^

TBD

Scratch
^^^^^^^

These instructions assume that you are on the Great Lakes HPC at UMich.

1. Add the following lines to your ``~/.bashrc`` file:

   .. code-block:: bash

      # Load required modules
      module load gcc              # GNU Compiler
      module load openmpi          # MPI Libraries
      module load python/3.9.12    # Python 3.9.12
      module load cmake            # CMake for build systems

      # PETSc Installation
      export PETSC_ARCH=real-opt
      export PETSC_DIR=<directory-path>/packages/petsc-3.15.3

      # CGNS Installation
      export CGNS_HOME=<directory-path>/packages/CGNS-4.4.0/opt-gfortran
      export PATH=$PATH:$CGNS_HOME/bin
      export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$CGNS_HOME/lib

   Replace ``<directory-path>`` with your installation directory path. Do not forget to ``source ~/.bashrc`` after editing.

2. Clone the repository:

   .. code-block:: bash

      $ git clone https://github.com/gorodetsky-umich/mdss.git

   Copy and execute the installation script:

   .. code-block:: bash

      $ cd mdss

      $ cp mdss/install_packages_gl.sh <directory-path>/

      $ chmod +x install_packages_gl.sh

      $ ./install_packages_gl.sh

Package Installation
--------------------

The following steps are common for personal computers and HPC systems:

1. Clone the repository:

   .. code-block:: bash

      $ git clone https://github.com/gorodetsky-umich/mdss.git

2. Navigate into the directory:
   
   .. code-block:: bash     
      
      $ cd mdss

3. Install the package:

   -  Without dependencies: 
      
      .. code-block:: bash       
         
         $ pip install .

   -  With dependencies:
      
      .. code-block:: bash      
         
         $ pip install . -r requirements.txt

   -  Editable installation:

      .. code-block:: bash
         
         $ pip install -e .

   - Editable installation with dependencies:

      .. code-block:: bash
         
         $ pip install -e . -r requirements.txt

Verification
------------

To verify the installation of packages, run a MACH-Aero tutorial
available available on the `MDO lab
website <https://mdolab-mach-aero.readthedocs-hosted.com/en/latest/machAeroTutorials/aero_adflow.html>`__.
The files required to run the tutprial can be obtained from the the
`MACH-Aero github repo <https://github.com/mdolab/MACH-Aero.git>`__.

**Follow the steps to run a MACH-Aero tutorial:**

1. Clone the MACH-Aero repo

.. code-block:: bash

   $ git clone https://github.com/mdolab/MACH-Aero.git

2. Create a new directory to run the tutorial

.. code-block:: bash

   $ mkdir <path-to-tutorial-directory>
   $ cd <path-to-tutorial-directory>

3. Copy the necessary files

.. code-block:: bash

   $ cp <path-to-mach-aero-directory>/tutorial/aero/analysis/wing_vol.cgns .
   $ cp <path-to-mach-aero-directory>/tutorial/aero/analysis/aero_run.py

4. Run the python file To run using one processor:

.. code-block:: bash

   python aero_run.py

To run using multiple processors:

.. code-block:: bash

   mpirun -np <nproc> python aero_run.py

.. note::

   Running using multiple processors helps to identify the problems with ``openmpi`` and ``petsc`` installations.

