# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))


# -- Project information -----------------------------------------------------

project = 'Multi-Disciplinary Simulation Suite'
copyright = '2025, Sinaendhran Pujali Elilarasan, Sanjan Muchandimath'
author = 'Sinaendhran Pujali Elilarasan, Sanjan Muchandimath'


# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',      # For Google/NumPy style docstrings
    'sphinx.ext.viewcode',      # Adds links to highlighted source code
    'sphinx_copybutton',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
html_theme = 'sphinx_rtd_theme'
#html_logo = 'assets/logo.svg'
html_static_path = ['_static']
html_css_files = ['extra.css']