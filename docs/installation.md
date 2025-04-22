# Installation and Dependencies

## Dependencies

### Core Framework Dependencies
The framework requires tools developed by NASA (OpenMDAO and MPhys) and the MDO Lab (MACH-Aero framework). The [MACH-Aero](https://mdolab-mach-aero.readthedocs-hosted.com/en/latest/index.html) framework houses all the core packages needed to run CFD simulations. Below is the list of software required:

- [`OpenMDAO`](https://github.com/OpenMDAO/OpenMDAO)
- [`MPhys>=2.0.0`](https://github.com/OpenMDAO/mphys)
- [`baseClasses`](https://github.com/mdolab/baseclasses)
- [`pySpline`](https://github.com/mdolab/pyspline)
- [`pyGeo`](https://github.com/mdolab/pygeo)
- [`IDWarp`](https://github.com/mdolab/idwarp)
- [`ADflow>=2.12.0`](https://github.com/mdolab/adflow)
- [`pyOptSparse`](https://github.com/mdolab/pyoptsparse)
- [`TACS>=3.8.0`](https://github.com/smdogroup/tacs) (Required for aerostructural simulations)
- [`funtofem>=0.3.9`](https://github.com/smdogroup/funtofem) (Required for aerostructural simulations)

These software packages may have additional third-party dependencies like PETSc and OpenMPI. A detailed guide on the additional dependencies required is available [here](https://mdolab-mach-aero.readthedocs-hosted.com/en/latest/installInstructions/installFromScratch.html).

### Python Libraries
The following Python libraries are also required:

- `numpy>=1.21`
- `scipy>=1.7`
- `mpi4py>=3.1.4`
- `petsc4py`
- `pyyaml`
- `matplotlib`
- `pandas`
- `pydantic`
- `niceplots`


---
## Getting Started
To begin using this framework, follow these steps:

1. **Create a Directory**  
   Set up a directory on your machine where you want to store this framework along with the necessary software packages.

    ```bash
    $ mkdir <directory-path> 
    $ cd <directory-path>
    ```

2. **Install Dependencies**  
   Follow the [Installation of Dependencies](#installation-of-dependencies) section to ensure all required dependencies are installed on your system.

3. **Install the Package**  
   Complete the setup by following the steps outlined in the [Package Installation](#package-installation) section.

By completing these steps, you'll have the framework ready for use.


## Installation of Dependencies

There are two types of installation methods available - from scratch and through Docker. If you are on a local machine, we recommend using Docker as it is the easiest option. If you are on an HPC machine, only the scratch installation method is available. Singularity support will be added later. Please follow the appropriate link.

- [Local machine (Docker)](#using-docker-recommended)
- [Local machine (Scratch)](#from-scratch)
- [HPC - Great Lakes (Singularity)](#singularity)
- [HPC - Great Lakes (Scratch)](#scratch)

### Local machine

#### Using Docker (Recommended)
Docker is highly recommended for ease of installation:

1. Setup Docker: If you do not have Docker installed in your system, follow the [Docker Guide](https://docs.docker.com/) to set it up.

2. Pull a Docker image: Official images for GCC and INTEL compilers are available [here](https://mdolab-mach-aero.readthedocs-hosted.com/en/latest/installInstructions/dockerInstructions.html). Follow the instructions in the link to pull an image compatible to your systems' architecture.

3. Initialize and start a container, follow the instructions mentioned [here](https://mdolab-mach-aero.readthedocs-hosted.com/en/latest/installInstructions/dockerInstructions.html#initialize-docker-container) to initialize and start a container. Mount the directory `<directory-path>` into the folder mentioned in [here](https://mdolab-mach-aero.readthedocs-hosted.com/en/latest/installInstructions/dockerInstructions.html#initialize-docker-container).

4. Inside the container, navigate to the `mount` directory and clone this repository following the instructions in the [Package Installation](#package-installation) section.

5. Run the testcase (TBD)

**_Note: If you are referencing any paths inside the container, they must be with respect to the container's folder architecture, not your host machine._**

#### From Scratch

To manually install all dependencies, we will refer to the instructions found in the [Scratch Installation Guide](https://mdolab-mach-aero.readthedocs-hosted.com/en/latest/installInstructions/installFromScratch.html).

(Sanjan needs to fix the local install bash file, unable to identify issue with petsc. Will do soon.)

### HPC Systems (Great Lakes)

#### Singularity 
TBD

#### Scratch

These instructions assume that you are on the Great Lakes HPC at UMich.

1. Add the following lines to your `~/.bashrc` file:
    ```bash
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
    ```
    Replace `<directory-path>` with your installation directory path. Do not forget to `source ~/.bashrc` after editing.

2. Clone the repository:
    ```bash
    $ git clone https://github.com/gorodetsky-umich/mdss.git
    ```

    Copy and execute the installation script:
    ```bash
    $ cd mdss

    $ cp mdss/install_packages_gl.sh <directory-path>/
    
    $ chmod +x install_packages_gl.sh

    $ ./install_packages_gl.sh
    ```

3. Run the testcase (TBD)

---

## Package Installation

The following steps are common for personal computers and HPC systems:

1. Clone the repository:
    ```bash
    $ git clone https://github.com/gorodetsky-umich/mdss.git
    ```
2. Navigate into the directory:
    ```bash
    $ cd mdss
    ```
3. Install the package:
    - Without dependencies:
        ```bash 
        $ pip install .
        ```
    - With dependencies:
        ```bash
        $ pip install . -r requirements.txt
        ```
    - Editable installation:
        ```bash
        $ pip install -e .
        ```

## Verification

To verify the installation of packages, run a MACH-Aero tutorial available available on the [MDO lab website](https://mdolab-mach-aero.readthedocs-hosted.com/en/latest/machAeroTutorials/aero_adflow.html). The files required to run the tutprial can be obtained from the the [MACH-Aero github repo](https://github.com/mdolab/MACH-Aero.git).

**Follow the steps to run a MACH-Aero tutorial:**

1. Clone the MACH-Aero repo
```bash
$ git clone https://github.com/mdolab/MACH-Aero.git
```

2. Create a new directory to run the tutorial
```bash
$ mkdir <path-to-tutorial-directory>
$ cd <path-to-tutorial-directory>
```
3. Copy the necessary files
```bash
$ cp <path-to-mach-aero-directory>/tutorial/aero/analysis/wing_vol.cgns .
$ cp <path-to-mach-aero-directory>/tutorial/aero/analysis/aero_run.py
```
4. Run the python file
To run using one processor:
```bash
python aero_run.py
```
To run using multiple processors:
```bash
mpirun -np <nproc> python aero_run.py
```
*_Note: Running using multiple processors helps to identify the problems with `openmpi` and `petsc` installations_*