# -- Configuration file for the Sphinx documentation builder ------------------
from pathlib import Path
from datetime import datetime
import subprocess
import json
import sys
import os

# -- Project information -----------------------------------------------------

variables = json.loads((Path(__file__).parent / "variables.json").read_text())
variables["copyright"] = variables["copyright"].replace(':year:', str(datetime.now().year))

project = variables["project"]
copyright = variables["copyright"].replace(':year:', '')
author = variables['author']

version = variables['version']
release = variables['release']


# -- Prevent circular imports in Sphinx ---------------------------------------

import sphinx.builders.html
import sphinx.builders.latex
import sphinx.builders.texinfo
import sphinx.builders.text
import sphinx.ext.autodoc


# -- Cyclonedds import without libs -------------------------------------------

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
os.environ['CYCLONEDDS_PYTHON_NO_IMPORT_LIBS'] = '1'

# -- Project information ------------------------------------------------------

project = 'Eclipse Cyclone DDS Python'
copyright = '2020, Eclipse Cyclone DDS Python Committers'
author = 'Eclipse Cyclone DDS Python Committers'

extlinks = {
    "c_repo":           ("https://github.com/eclipse-cyclonedds/cyclonedds/", None),
    "py_repo":          ("https://github.com/eclipse-cyclonedds/cyclonedds-python/", None),
    "venv":             ("https://docs.python.org/3/tutorial/venv.html", None),
    "poetry":           ("https://python-poetry.org/", None),
    "pipenv":           ("https://pipenv.pypa.io/en/latest/", None),
    "pyenv":            ("https://github.com/pyenv/pyenv", None),
    "py_installing":    ("https://docs.python.org/3/installing/index.html", None)
}


# -- General configuration ----------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.extlinks',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    "sphinx.ext.viewcode"
]
autodoc_mock_imports=["ctypes.CDLL", "cyclonedds._clayer", "cyclonedds.__library__"]
autodoc_member_order = 'bysource'
autodoc_typehints = 'description'

intersphinx_mapping = {'python': ('https://docs.python.org/3', None)}

napoleon_google_docstring = False
napoleon_numpy_docstring = True

templates_path = ['templates']
html_static_path = ['static']
html_title = f"{project}, {version}"
html_short_title = html_title
language = 'en'

exclude_patterns = ['Thumbs.db', '.DS_Store', '_build', '**/*.part.rst']
needs_sphinx = '4.0'

try:
    import piccolo_theme
    extensions.append('piccolo_theme')
    html_theme = 'piccolo_theme'
    html_css_files = ['css/helpers.css']
    html_js_files = ['js/helpers.js']
except ImportError:
    import warnings
    warnings.warn("piccolo_theme is not installed. Falling back to alabaster.")
    html_theme = 'alabaster'

pygments_style = 'friendly'

# -- Export variables to be used in RST --------------------------------------

rst_epilog = '\n'.join(map(lambda x: f".. |var-{x[0]}| replace:: {x[1]}", variables.items()))

# -- Configuration file for the Sphinx documentation builder ------------------
