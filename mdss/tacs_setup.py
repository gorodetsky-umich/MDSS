import copy
import numpy as np
from tacs import elements, constitutive, functions

class tacs_setup():
    
    def __init__(self, structural_properties, load_info, outputdir):
        self.structural_properties = {key: float(value) for key, value in structural_properties.items()}
        self.load_info = load_info
        self.outputdir = outputdir

    # Callback function used to setup TACS element objects and DVs
    def element_callback(self, dvNum, compID, compDescript, elemDescripts, specialDVs, **kwargs):
        #print(self.structural_properties)
        print(self.load_info)
        # Get Structural Properties
        # Material properties
        rho = self.structural_properties['rho']     # density (kg/m^3)
        E = self.structural_properties['E']         # Young's modulus (Pa)
        nu = self.structural_properties['nu']       # Poisson's ratio
        kcorr = self.structural_properties['kcorr'] # shear correction factor
        ys = self.structural_properties['ys']       # yield stress
        t = self.structural_properties['t']         # shell thickness (m)
        # Setup (isotropic) property and constitutive objects
        prop = constitutive.MaterialProperties(rho=rho, E=E, nu=nu, ys=ys)
        # Set one thickness dv for every component
        con = constitutive.IsoShellConstitutive(prop, t=t, tNum=dvNum)

        # For each element type in this component,
        # pass back the appropriate tacs element object
        transform = None
        elem = elements.Quad4Shell(transform, con)
        return elem

    def problem_setup(self, scenario_name, fea_assembler, problem):
        """
        Helper function to add fixed forces and eval functions
        to structural problems used in tacs builder
        """
        g = np.array(self.load_info['g'])
        inertial_load_factor = self.load_info['inertial_load_factor']

        # Add TACS Functions
        problem.setOption('outputdir', self.outputdir)
        problem.addFunction('ks_vmfailure', functions.KSFailure, safetyFactor=1.0, ksWeight=100.0)
        problem.addFunction('mass', functions.StructuralMass)
        problem.addInertialLoad(inertial_load_factor* g)
