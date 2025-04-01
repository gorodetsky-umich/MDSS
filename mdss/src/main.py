import os
import time
import copy
from datetime import date, datetime

import pandas as pd
import numpy as np
import yaml
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.lines import Line2D
from matplotlib.legend import Legend
import niceplots
from mpi4py import MPI

from mdss.utils.helpers import load_yaml_file, load_csv_data, make_dir, print_msg, MachineType
from mdss.src.main_helper import execute, submit_job_on_hpc
from mdss.resources.misc_defaults import def_plot_options
from mdss.resources.yaml_config import ref_plot_options, check_input_yaml


comm = MPI.COMM_WORLD

class simulation():
    """
    Executes aero(structural) simulations using the `Top` class defined in [`aerostruct.py`](aerostruct.py).

    This class sets up and runs aerodynamic and/or aerostructural simulations based on input parameters provided via a YAML configuration file. It validates the input, manages directories, and handles outputs, including summary files. The simulations are run using subprocesses.

    Inputs
    ----------
    - **info_file** : str
        Path to the YAML file containing simulation configuration and information.
    
    Methods
    -------
    **run()**
        Helps to execute the simulation on either a local machine or an HPC.
    """

    def __init__(self, info_file):
        # Validate the input yaml file
        check_input_yaml(info_file)
        msg = f"YAML file validation is successful"
        print_msg(msg, None, comm)

        self.info_file = info_file
        self.sim_info = load_yaml_file(self.info_file, comm)
        self.out_dir = os.path.abspath(self.sim_info['out_dir'])
        self.machine_type = MachineType.from_string(self.sim_info['machine_type'])  # Convert string to enum
        # Additional options
        self.final_out_file = os.path.join(self.out_dir, "overall_sim_info.yaml") # Set the overall simulation info file name.
        self.subprocess_flag = True # To toggle opting subprocess.
        self.record_subprocess = False # To toggle to record subprocess output.

        # Create the output directory if it doesn't exist
        make_dir(self.out_dir, comm)

    
    ################################################################################
    # Code for user to run simulations
    ################################################################################
    def run(self):
        """
        Executes the simulation on either a local machine or an HPC. 

        This method checks the simulation settings from the input YAML file. Based on the machine_type, it either runs the simulation locally or generates an HPC job script for execution.

        Notes
        -----
        - For local execution, it directly calls `run_problem()`.
        - For HPC execution, it creates a Python file and a job script, then submits the job.
        """
        sim_info_copy = copy.deepcopy(self.sim_info)
        if self.machine_type == MachineType.LOCAL: # Running on a local machine
            execute(self)

        elif self.machine_type == MachineType.HPC: # Running on a HPC currently supports Great Lakes.
            submit_job_on_hpc(sim_info_copy, self.info_file, comm) # Submit job script

                       
################################################################################
# Code for Post Processing
################################################################################
class post_process:
    """
    Performs post-processing operations for simulation results.

    This class provides functionality to visualize and compare aerodynamic performance data
    such as Lift Coefficient (C<sub>L</sub>) and Drag Coefficient (C<sub>D</sub>) against Angle of Attack (Alpha),
    based on the simulation configuration provided via a YAML file.

    Inputs
    ------
    - **out_dir**: str  
        Path to the output directory. The output directory should contain the final out file from the simulation.

    Methods
    -------
    - **gen_case_plots()**  
        Generates case-wise plots comparing experimental and simulation results across scenarios and refinement levels.

    - **compare_scenarios(scenarios_list, plt_name)**  
        Generates a combined plot comparing selected scenarios across multiple hierarchies and cases.

    - **_add_plot_from_csv(axs, csv_file, **kwargs)**  
        Adds a single line plot for C<sub>L</sub> and C<sub>D</sub> from a CSV file to existing subplots.

    - **_add_scenario_level_plots(axs, scenario_name, exp_data, mesh_files, scenario_out_dir, **kwargs)**  
        Adds plots for a given scenario, including experimental and refinement-level simulation results.

    - **_create_fig(title, niceplots_style=None)**  
        Initializes and returns a styled matplotlib figure with two subplots.

    - **_get_marker_style(idx)**  
        Returns a marker style based on the index, used to distinguish between scenarios visually.
    """

    def __init__(self, out_dir: str, plot_options: dict={}):
        self.out_dir = os.path.abspath(out_dir)
        self.final_out_file = os.path.join(self.out_dir, "overall_sim_info.yaml") # Setting the overall simulation info file.
        try:
            self.sim_out_info = load_yaml_file(self.final_out_file, comm)
        except:
            msg = f"{self.final_out_file} does not exist. Make sure it is the right output directory."
            print_msg(msg, None, comm)
            raise FileNotFoundError("")

        # Additional Options
        plot_options = def_plot_options
        plot_options.update(plot_options)
        self.plot_options = ref_plot_options.model_validate(plot_options)
        
    def gen_case_plots(self):
        """
        Generates plots comparing experimental data with simulation results for each case and hierarchy.

        This method loops through all hierarchies, cases, and scenarios in the simulation output,
        and generates side-by-side plots of C<sub>L</sub> and C<sub>D</sub> versus Angle of Attack (Alpha) for each case.
        Each scenario is plotted using a distinct marker, and each mesh refinement level is plotted using a different color.
        Experimental data, if provided, is overlaid for validation.

        Outputs
        --------
        - *PNG File*:
            A comparison plot showing C<sub>L</sub> and C<sub>D</sub> vs Alpha for all scenarios and refinement levels of a case.  
            The file is saved in the scenario output directory for each case using the case name.

        Notes
        ------
        - Experimental data is optional. If not provided, only simulation data is plotted.
        - Markers distinguish scenarios; colors distinguish mesh refinement levels.
        - A shared legend is placed outside the figure to indicate scenario markers.
        - Axis spines are formatted using `niceplots.adjust_spines()` and figures are saved at high resolution (400 dpi).
        - Figures are titled using the case name and saved using `niceplots.save_figs()`.
        """
        sim_out_info = copy.deepcopy(self.sim_out_info)
        for hierarchy, hierarchy_info in enumerate(sim_out_info['hierarchies']): # loop for Hierarchy level
            for case, case_info in enumerate(hierarchy_info['cases']): # loop for cases in hierarchy
                scenario_legend_entries = []
                fig, axs = self._create_fig(case_info["name"].replace("_", " ").upper()) # Create Figure
                for scenario, scenario_info in enumerate(case_info['scenarios']): # loop for scenarios that may present
                    scenario_out_dir = scenario_info['sim_info']['scenario_out_dir']
                    plot_args = {
                        'marker': self._get_marker_style(scenario),
                        'label': scenario_info['name'].replace("_", " ").upper(),
                    }
                    # To generate plots comparing the refinement levels
                    scenario_legend_entry = self._add_scenario_level_plots(axs, scenario_info['name'], scenario_info.get('exp_data', None), case_info['mesh_files'], scenario_out_dir, **plot_args)
                    scenario_legend_entries.append(scenario_legend_entry)
                ################################# End of Scenario loop ########################################
                self._set_legends(fig, axs, scenario_legend_entries)
                fig_name = os.path.join(os.path.dirname(scenario_out_dir), case_info['name'])
                niceplots.save_figs(fig, fig_name, ["png"], format_kwargs={"png": {"dpi": 400}}, bbox_inches="tight")

    def compare_scenarios(self, scenarios_list: list[dict], plt_name: str):
        """
        Generates a combined plot comparing specific scenarios across hierarchies and cases.

        This function creates a figure with two subplots: one for C<sub>L</sub> vs Alpha and another for C<sub>D</sub> vs Alpha.
        It overlays selected scenarios (across different cases and hierarchies) and creates a shared legend
        to highlight which scenario each marker represents.

        Inputs 
        -------
        - **scenarios_list**: list[dict]  
            A list of dictionaries, each defining a scenario to be compared.  
            Each dictionary must contain the following keys:
                - *hierarchy*: str  
                    Name of the hierarchy the scenario belongs to.
                - *case*: str  
                    Name of the case within the hierarchy.
                - *scenario*: str  
                    Name of the scenario to be plotted.
            
            Optional key:
                - 'mesh_files': list[str]  
                    List of mesh refinement levels to include for that scenario. If not specified, defaults to all mesh files under the case.

        - **plt_name**: str  
            Name used for the plot title and the saved file name (PNG format).

        Outputs
        --------
        - **PNG File**:
            A side-by-side comparison plot showing C<sub>L</sub> and C<sub>D</sub> vs Alpha for all selected scenarios.  
            The plot is saved in the output directory of the last processed scenario.

        Notes
        ------
        - Each scenario is plotted using a consistent marker, with colors indicating refinement levels.
        - Experimental data is included when available.
        - A shared legend (outside the plot) shows scenario identifiers and their corresponding markers.
        - If multiple scenarios share the same marker (due to index reuse), modify `_get_marker_style()` to expand the list.
        """
        sim_out_info = copy.deepcopy(self.sim_out_info)
        fig, axs = self._create_fig(plt_name.replace("_", " ").upper()) # Create Figure
        scenario_legend_entries = []
        found_scenarios = False
        count = 0 # To get marker style
        for s in scenarios_list:
            for hierarchy_info in sim_out_info['hierarchies']: # loop for Hierarchy level
                for case_info in hierarchy_info['cases']: # loop for cases in hierarchy
                    for scenario, scenario_info in enumerate(case_info['scenarios']): # loop for scenarios that may present
                        if (s['hierarchy'] == hierarchy_info['name'] and s['case'] == case_info['name'] and s['scenario'] == scenario_info['name']): # Add current scenario's plot
                            found_scenarios = True
                            mesh_files = s.get('mesh_files', case_info['mesh_files'])
                            scenario_out_dir = scenario_info['sim_info'].get('scenario_out_dir', '.')
                            label = f"{case_info['name']} - {scenario_info['name']}"
                            plot_args = {
                                'marker': self._get_marker_style(count),
                                'label': label.replace("_", " ").upper(),
                            }
                            scenario_legend_entry = self._add_scenario_level_plots(axs, scenario_info['name'], scenario_info.get('exp_data', None), mesh_files, scenario_out_dir, **plot_args)
                            scenario_legend_entries.append(scenario_legend_entry)
                            count+=1

        if not found_scenarios:
            return ValueError("None of the scenarios are found")

        self._set_legends(fig, axs, scenario_legend_entries)
        fig_name = os.path.join(self.out_dir, plt_name)
        niceplots.save_figs(fig, fig_name, ["png"], format_kwargs={"png": {"dpi": 400}}, bbox_inches="tight")
                    
    def _add_plot_from_csv(self, axs, csv_file:str, **kwargs):
        """
        Adds a plot of Angle of Attack vs Lift and Drag Coefficients from a CSV file.

        This method expects two subplots: one for C<sub>L</sub> (Lift Coefficient) vs Alpha, and one for C<sub>D</sub> (Drag Coefficient) vs Alpha.
        The CSV must contain the columns: 'Alpha', 'CL', and 'CD'.

        Inputs
        -------
        - **axs**: list[matplotlib.axes._subplots.AxesSubplot]
            A list of two matplotlib axes. axs[0] is used for plotting C<sub>L</sub> vs Alpha, and axs[1] for C<sub>D</sub> vs Alpha.
        
        - **csv_file**: str
            Path to the CSV file containing simulation or experimental data. The file must have 'Alpha', 'CL', and 'CD' columns.
        
        - ****kwargs**:
            Optional keyword arguments to customize the plot appearance.
                - *label* : str  
                    Label for the plotted line (used in legends). Default is None.
                - *color* : str  
                    Color of the plotted line. Default is 'black'.
                - *linestyle* : str  
                    Line style for the plotted line. Default is '--'.
                - *marker* : str  
                    Marker style for the data points. Default is 's'.

        Outputs
        --------
        - **Adds plot lines to the existing subplots**:
            - axs[0] will have a line for C<sub>L</sub> vs Alpha.
            - axs[1] will have a line for C<sub>D</sub> vs Alpha.

        Notes
        ------
        - If the CSV file cannot be read or is missing required columns, a warning is printed and the plot is skipped.
        """
        label = kwargs.get('label', None)
        color = kwargs.get('color', 'black')
        linestyle = kwargs.get('linestyle', '--')
        marker = kwargs.get('marker', 's')

        sim_data = load_csv_data(csv_file, comm)
        if sim_data is not None:
            for ax, y_key in zip(axs, ['CL', 'CD']):
                ax.plot(
                    sim_data['Alpha'], sim_data[y_key],
                    label=label,
                    color=color,
                    linestyle=linestyle,
                    marker=marker
                )
        else:
            msg = f"{csv_file} is not readable.\nContinuing to plot without '{label}' data."
            print_msg(msg, 'warning', comm)

    def _add_scenario_level_plots(self, axs, scenario_name, exp_data, mesh_files, scenario_out_dir, **kwargs):
        """
        Adds plots for a specific scenario (experimental + simulation) to the existing subplots.

        This method:
        - Plots experimental data for the scenario if a valid CSV path is provided.
        - Loops over mesh refinement levels and plots ADflow results from each mesh file.
        - Creates a `Line2D` entry for the scenario to be used in an external legend.

        Inputs
        -------
        - **axs**: list[matplotlib.axes._subplots.AxesSubplot]  
            A list of two matplotlib axes. axs[0] is for C<sub>L</sub> vs Alpha, and axs[1] is for C<sub>D</sub> vs Alpha.

        - **scenario_name**: str  
            Name of the scenario, used for labeling and legend entry.

        - **exp_data**: str or None  
            Path to the experimental data CSV file. If None, no experimental data is plotted.

        - **mesh_files**: list[str]  
            List of mesh refinement levels to be plotted (e.g., ['coarse', 'medium', 'fine']).

        - **scenario_out_dir**: str  
            Path to the scenario's output directory, where refinement-level folders are located.

        - ****kwargs**:
            Optional styling arguments passed to `_add_plot_from_csv()`:
                - *label* : str  
                    Label for the scenario used in the external legend. Defaults to a cleaned version of `scenario_name`.
                - *color* : str  
                    Base color for the scenario legend marker. Defaults to 'black'.
                - *linestyle* : str  
                    Line style for the plots. Will be set to '--' for experimental data, and '-' for simulation data.
                - *marker* : str  
                    Marker style for the scenario legend entry. Defaults to 's'.
                - *markersize* : int  
                    Size of the legend marker. Defaults to 10.

        Outputs
        --------
        - **scenario_legend_entry**: matplotlib.lines.Line2D  
            A legend entry representing the scenario (based on marker and label) to be added to the external legend.

        Notes
        ------
        - Experimental data will only be plotted if the provided `exp_data` file is valid.
        - Simulation results are expected to be located in `${scenario_out_dir}/${mesh_file}/ADflow_output.csv`.
        """
        scenario_label = scenario_name.replace("_", " ")

        label = kwargs.get('label', scenario_label)
        color = kwargs.get('color', 'black')
        linestyle = kwargs.get('linestyle', '-')
        marker = kwargs.get('marker', 's')
        markersize = kwargs.get('markersize', 10)

        kwargs['linestyle'] = '--' # Modify the linestyle
        #kwargs['label'] = f"{scenario_label}, Experimental" # Set label for experimental data
        kwargs['label'] = None
        self._add_plot_from_csv(axs, exp_data, **kwargs) # To add experimental data to the plot

        colors = niceplots.get_colors_list() # Get colors from nice plots

        for ii, mesh_file in enumerate(mesh_files): # Loop for refinement levels
            refinement_level_dir = os.path.join(scenario_out_dir, f"{mesh_file}")
            ADflow_out_file = os.path.join(refinement_level_dir, "ADflow_output.csv")
            # Update kwargs
            kwargs['linestyle'] = '-'
            kwargs['color'] = colors[ii]
            kwargs['label'] = f"{mesh_file}"
            self._add_plot_from_csv(axs, ADflow_out_file, **kwargs) # To add simulation data to the plots
        
        scenario_legend_entry = Line2D([0], [0], marker=marker, color=color, linestyle='', markersize=markersize, label=label) # Create a legend entry for the scenario
        return scenario_legend_entry
    
    def _create_fig(self, title, niceplots_style=None):
        """
        Creates a matplotlib figure with subplots for C<sub>L</sub> and C<sub>D</sub> vs Alpha.

        This method initializes the figure layout and applies consistent niceplots styling.

        Inputs
        -------
        - **title**: str  
            Title to be shown at the top of the figure.
        
        - **niceplots_style**: str or None  
            Optional name of the niceplots style to apply. If None, uses `self.niceplots_style`.

        Outputs
        --------
        - **fig**: matplotlib.figure.Figure  
            The created figure object.

        - **axs**: list[matplotlib.axes._subplots.AxesSubplot]  
            A list of two subplots for plotting C<sub>L</sub> and C<sub>D</sub> vs Alpha.

        Notes
        ------
        - Subplots are pre-configured with axis titles, labels, and grids.
        """
        if niceplots_style is None:
            niceplots_style = self.plot_options.niceplots_style
        
        figsize = self.plot_options.figsize

        plt.style.use(niceplots.get_style(niceplots_style))
        fig, axs = plt.subplots(1, 2, figsize=(14, 6))
        fig.suptitle(title)

        titles = ['$C_L$ vs Alpha', '$C_D$ vs Alpha']
        ylabels = ['$C_L$', '$C_D$']

        for ax, subplot_title, ylabel in zip(axs, titles, ylabels):
            ax.set_title(subplot_title)
            ax.set_xlabel('Alpha (deg)')
            ax.set_ylabel(ylabel)
            ax.grid(True)

        return fig, axs
    
    def _set_legends(self, fig, axs, scenario_legend_entries):

        mesh_handles, mesh_labels = axs[0].get_legend_handles_labels()
        # Create the legends
        scenario_legend = Legend(fig, handles=scenario_legend_entries,
                                labels=[h.get_label() for h in scenario_legend_entries],
                                loc='center left',
                                bbox_to_anchor=(1.0, 0.25),
                                title='Scenarios',
                                frameon=True,
                                fontsize=10,
                                labelspacing=0.3)

        mesh_legend = Legend(fig, handles=mesh_handles,
                            labels=mesh_labels,
                            loc='center left',
                            bbox_to_anchor=(1.0, 0.75),
                            title='Meshes',
                            frameon=True,
                            fontsize=10,
                            labelspacing=0.3)

        fig.add_artist(scenario_legend)
        fig.add_artist(mesh_legend)
        niceplots.adjust_spines(axs[0])
        niceplots.adjust_spines(axs[1])
        fig.tight_layout(rect=[0, 0, 0.95, 1])

    def _get_marker_style(self, idx):
        """
        Function to loop though the marker styles listed here.
        Add more if needed.

        Inputs
        -------
        - **idx**: int
            Index of the current loop
        
        Outputs
        --------
        - **Marker Style**: str
            Marker style for the current index
        """
        markers = ['s', 'o', '^', 'D', 'v', '*', 'X', 'P']
        return markers[idx % len(markers)]