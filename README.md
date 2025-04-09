# Multi-Disciplinary Simulation Suite (MDSS)

`mdss` is a Python package designed for running Aerodynamic (ADflow) and Aerostructural (TACS) simulations using MPhys and OpenMDAO. This package provides streamlined functions to automate simulations.
For detailed install instructions and usage, visit the [documentation page](https://gorodetsky-umich.github.io/MDSS/).

## Dependencies

The package requires the following libraries, that can be installed with `pip`:

- `numpy>=1.21`
- `scipy>=1.7`
- `mpi4py>=3.1.4`
- `pyyaml`
- `matplotlib`
- `pandas`
- `petsc4py`

Additionally, the following packages are also needed but may require manual installation:

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

A bash shell script is provided to download and install all the required dependencies and software programs provided by the MDO lab. It is assumed that the user is working on a local Debian based machine. 

However, we recommend using Docker. Images are available for both GCC and INTEL compilers [here](https://mdolab-mach-aero.readthedocs-hosted.com/en/latest/installInstructions/dockerInstructions.html#) 

## Instructions for Installation

After installing the required dependencies and softwares (or by starting initializing a docker container), users can install `mdss` using the following commands:

1. Clone the repository:

    ```bash
    git clone https://github.com/gorodetsky-umich/MDSS.git
    ```

2. Navigate into the directory:

    ```bash
    cd MDSS
    ```

3. To install the package without dependencies:

    ```bash
    pip install .
    ```
    To install the package along with dependencies listed in `requirements.txt`:
    ```bash
    pip install . -r requirements.txt
    ```
    For an editable installation:
    ```bash
    pip install -e .
    ```
