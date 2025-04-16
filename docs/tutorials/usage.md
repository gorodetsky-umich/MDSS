# Usage
## Run a script from examples
The [script](#running-simulations) below runs a simulation of the NACA 0012 Airfoil, and is included in the `examples` folder. 

**To run the above python script:**

- Copy the examples directory to a different location:

```bash 
$ cp -r <path-to-repository>/examples <path-to-examples-directory> 
```

- Navigate into the directory:

```bash
$ cd <path-to-examples-directory> 
```

- Run the python script:

```bash 
$ python example.py --inputFile <path-to-input-yaml-file>
```

**_Note:_**

- *_Do not use `mpirun` to run a script with `mdss`. Because, it runs simulations on subprocesses and using `mpirun` results in an error_*
- *_Example input yaml files to run on personal computers are stored in `examples/inputs` directory, and for Great Lakes HPC cluster, an example file is stored in `examples/inputs/GL`_*
- *_Make sure to modify the file and file paths to absolute paths in the yaml file when running in a docker container._*

Use `examples/inputs/naca0012_sinInfo.yaml` or `examples/inputs/GL/naca0012_sinInfo.yaml`(for Great Lakes) to test the package with NACA0012 airfoil.

After execution, the following results are expected which are saved in the specified output directory.

- A copy of the input yaml file in the output directory.
- `overall_sim_info.yaml` in the output directory.
- `ADflow_Results.png` in each experimental level directory, that is a plot comparing C<sub>L</sub>, and C<sub>D</sub> values at all refinement levels to the expeimental data(if provided).

<p align="center">
  <img src="../test_run_doc/ADflow_Results.png" alt="Comparision plot" width="800">
</p>

- `ADflow_output.csv` in each refinement level directory, that is a file containg Angle of Attack(AoA), C<sub>L</sub>, and C<sub>D</sub> data.
- `aoa_<aoa>.yaml` in aoa level directory, that contains the simulation information particular to that angle of attack.
- Default ADflow outputs: A tecplot file, a CGNS surface file, and a CGNS volume file.

## Example usage
Here are quick examples of how to different classes and functions in `mdss`:

### Running Simulations
```python
from mdss import simulation

# Initialize the runner with configuration file
sim = simulation('/path/to/input-yaml-file')

# Run the simulation series
sim.run()
```

### Read existing simualtion data or generate data

The function `get_sim_data` can be used to get existing simulation data that was generated after a simulation, as a dictionary.

The function provides the flexibility of using the input YAML file or  the `overall_sim_info.yaml` file that is generated and stored in the outptut directory after the completion of simulations, as inputs.

```python
from utils import get_sim_data

# Specify the path to the input file.
info_file = '/path/to/input-yaml-file'

# Call the function to get simulation data as a dictionary
sim_data = get_sim_data(info_file)

# Print the dictionary
print(sim_data)
```
### Custom Simulations

The `run_naca0012` and `run_30p30n` functions allow users to run simulations without the need to generate an input YAML file. Instead, users can supply a [dictionary](#template-for-input-dictionary) of basic parameters. These functions load the respective YAML files and update it with the information provided by the user. 

Users can specify an output directory to save the simulation data; otherwise, the data will be stored in a temporary file and deleted after the simulation completes.

**_Note: These functions are intended to use in a python script. If you want to run on a HPC, create a job script and submit it manually._**

#### Template for Input Dictionary

```python
case_info = {
    'out_dir': '',  # (Optional) str, path to output directory
    'meshes_folder_path': '', # str, path to the folder containing mesh files.
    'mesh_files': [],         # list[str], list of mesh file names.
    'aoa_list': [],           # list[float], list of angles of attack to simulate.
    'solver_parameters': {},  # (Optional) dict, dictionary of solver-specific parameters to update.
}
```

---

#### Example Usage

```python
from mdss.utils import run_naca0012

case_info = {
    'meshes_folder_path': '/path/to/meshes',
    'mesh_files': ['naca0012_L0.cgns'],
    'aoa_list': [0],
}

sim_data = run_naca0012(case_info)

print(sim_data)
```

## Additional Information
### Grid Files
Grids for NACA 0012 and Mc Donnell Dolugas 30P-30N are provided under `examples/grids` in the examples directory. The other grids (CRM clean, and DLR High-Lift) including Naca 0012 and 30P-30N can be found at [Dropbox folder](https://www.dropbox.com/scl/fo/fezdu5be849c78vze7l19/ACCsSHpLGEwCcyFEPWj2FB0?rlkey=ixbr0606y3vx5eadrs61b9cz3&st=i4evwxed&dl=0).

### Experimental data
Experimental data for NACA 0012 and Mc Donnell Dolugas 30P-30N are provided under `examples/exp_data` in the examples directory. The other dat (CRM clean, and DLR High-Lift) including Naca 0012 and 30P-30N, and their references can be found at [Dropbox folder](https://www.dropbox.com/scl/fo/18rcs9bh0qmf19ymptrt2/AHx-xyYSXk_wGXqhvVV2yMM?rlkey=kp0vovsegpddfn78wfjiv8gbi&st=2czi5hbu&dl=0).
