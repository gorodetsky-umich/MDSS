# Introduction
The `mdss` package is a Python-based tool designed to streamline the execution and data management of Aerodynamic and Aerostructural simulations. It integrates with MPhys to provide a structured framework for running simulations and organizing the resulting data in a hierarchical manner.

This package is particularly suited for projects involving multiple configurations or test cases, ensuring that simulation results are stored and categorized systematically.

### Key Features
- Automates the execution of multiple aerodynamic and aerostructural simulations in sequence, reducing manual intervention.
- Streamlines simulation management using ADflow and TACS via Mphys and OpenMDAO.
- Provides built-in utilities for comparison plots, modifying input files, and managing simulation results efficiently.
- Enables efficient case setup and result storage for systematic analysis.

### Inputs

The `mdss` package requires an **YAML Configuration File** as an input

**A YAML file specifying:**

- Simulation hierarchy.
- Mesh files and solver parameters.
- Scenarios (e.g., Reynolds number, Mach number, and angle of attack).

### Outputs

The outputs of `mdss` are stored in directories organized according to the simulation hierarchy. These include:

1. **Simulation Data:**

    Results such as C<sub>L</sub>, C<sub>D</sub>, and Wall Time are saved in CSV and YAML formats.

2. **Hierarchical Directory Structure:**

    Output directories follow the YAML-defined hierarchy, allowing for easy navigation of results.

3. **Visualization:**

    Comparison plots (e.g., experimental vs. simulated data) are generated in PNG format.

### Example Hierarchy

The package organizes simulation data into a clear and logical hierarchy. An example of this structure, that has been used in the tutorials is shown below:

```
Project
    |
    |---- 2D Clean
    |       |
    |       |---- NACA 0012
    |
    |---- 2D High-Lift
    |       |
    |       |---- Mc Donnell Dolugas 30P-30N
    |
    |---- 3D Clean
    |       |
    |       |---- NASA CRM clean Configuration
    |
    |---- 3D High-Lift
    |       |
    |       |---- DLR High-Lift Configuration
    |
    |---- 3D Wing-Aerostructural
            |
            |---- Mach Aero Wing
```
Explanation of the Hierarchy:

1. **Project:** Categorizes the type of aerodynamic and aerostructural analysis, such as clean flow or high-lift studies, in 2D or 3D configurations.

2. **2D Clean:** Simulations for 2D configurations without high-lift devices (e.g., NACA 0012 airfoil).

3. **2D High-Lift:** Simulations for 2D configurations with high-lift devices (e.g., McDonnell Douglas 30P-30N airfoil).

4. **3D Clean:** Simulations for 3D configurations without high-lift devices (e.g., NASA Common Research Model Clean Configuration).

5. **3D High-Lift:** Simulations for 3D configurations with high-lift devices (e.g., DLR High-Lift Configuration).

6. **3D Wing-Aerostructural:** Aerostructural simulations of a wing (e.g., the Mach Aero Wing used in tutorials in MACH AERO framework of the mdolab).