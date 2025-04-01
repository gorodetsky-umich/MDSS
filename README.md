# Multi-Disciplinary Simulation Suite (MDSS)

`mdss` is a Python package designed for running a series of Aerodynamic and Aerostructural simulations using ADflow, and TACS simulations with mphys and openMDAO. This package provides streamlined functions to automate simulation test cases.

For detailed install instructions and usage visit the [documentation page](https://gorodetsky-umich.github.io/mdss/).

## Dependencies

The package requires the following libraries, which can automatically be installed with `pip`:

- `numpy>=1.21`
- `scipy>=1.7`
- `mpi4py>=3.1.4`
- `pyyaml`
- `matplotlib`
- `pandas`
- `petsc4py`

Additionally, the following packages are also needed but may require manual installation:

- [`OpenMDAO`](https://github.com/OpenMDAO/OpenMDAO)
- [`MPhys`](https://github.com/OpenMDAO/mphys)
- [`baseClasses`](https://github.com/mdolab/baseclasses)
- [`pySpline`](https://github.com/mdolab/pyspline)
- [`pyGeo`](https://github.com/mdolab/pygeo)
- [`IDWarp`](https://github.com/mdolab/idwarp)
- [`ADflow`](https://github.com/mdolab/adflow)
- [`pyOptSparse`](https://github.com/mdolab/pyoptsparse)
- [`TACS`](https://github.com/smdogroup/tacs) (Required for aerostructural simulations)
- [`funtofem`](https://github.com/smdogroup/funtofem) (Required for aerostructural simulations)

A bash shell script is provided to download and install all the required dependencies and software programs provided by the MDO lab. It is assumed that the user is working on a local Debian based machine. 

However, we recommend using Docker. Images are available for both GCC and INTEL compilers [here](https://mdolab-mach-aero.readthedocs-hosted.com/en/latest/installInstructions/dockerInstructions.html#) 

## Instructions for Installation

To install `mdss`, use the following commands:

1. Clone the repository:

    ```bash
    git clone https://github.com/gorodetsky-umich/mdss.git
    ```

2. Navigate into the directory:

    ```bash
    cd mdss
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
