# Outputs

The `mdss` package organizes simulation results into a structured directory hierarchy. This hierarchy mirrors the simulation setup defined in the YAML file.

### Structure of the Output Directory

<p align="center">
  <img src="../output_directory_structure.svg" alt="Structure of the Output Directory" width="800">
</p>

## File Types

1. **CSV Files**:
    - Stored in Refinement Level directory 
    - Contain simulation data, including:
        - Coefficient of Lift (C<sub>L</sub>)
        - Coefficient of Drag (C<sub>D</sub>)
        - Wall Time

2. **YAML Files**:
    - Two types:
        - Per-case YAML files (`out.yaml`) stored in each AoA directory.
        - A summary YAML file for the entire simulation.


3. **PNG Files**:
    - Comparison plots of experimental vs. simulated data, stored in the corresponding experimental level level directory.


This structure ensures that simulation results are easy to navigate and analyze.


