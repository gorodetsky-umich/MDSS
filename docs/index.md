# Multi-Disciplinary Simulation Suite (MDSS)

[`mdss`](https://github.com/gorodetsky-umich/mdss.git) is a Python package designed to automate the execution of **aerodynamic** and **aerostructural** simulations using [**ADflow**](https://mdolab-adflow.readthedocs-hosted.com/en/latest/) and [**TACS**](https://smdogroup.github.io/tacs/), integrated with [**Mphys**](https://openmdao.github.io/mphys/) and [**OpenMDAO**](https://openmdao.org/). It simplifies running multiple test cases sequentially, streamlining simulation setup, execution, and post-processing.

- [Installation](installation.md)
- [Introduction](tutorials/introduction.md)
- [Usage](tutorials/usage.md)
- [Test Cases](tutorials/test_cases.md)
- [Source Documentation](reference/index.md)

## Key Features
- Automates the execution of multiple aerodynamic and aerostructural simulations in sequence, reducing manual intervention.
- Streamlines simulation management using ADflow and TACS via Mphys and OpenMDAO.
- Provides built-in utilities for comparison plots, modifying input files, and managing simulation results efficiently.
- Enables efficient case setup and result storage for systematic analysis.

## Getting Started
### Installation
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
    pip install -e .
    ```
For detailed information on dependencies and install instructions, check the [installation page](installation.md).

### Running a Simulation
Here is a quick example on how to use the `mdss`:
```python
from mdss.run_sim import run_sim

# Initialize the runner with configuration file
sim = run_sim('/path/to/input-yaml-file')

# Run the simulation series
sim.run()

# Analyze results
sim.post_process()
```
Detailed information on the usage can be found on the [tutorials page](tutorials/introduction.md).