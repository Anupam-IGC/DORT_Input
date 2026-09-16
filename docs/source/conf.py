from pathlib import Path
import os
import sys

# The project is currently a collection of top-level Python modules rather than
# an installed package. Add the repository root so autodoc can import them.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

project = "DORT R-Z Input Preparation API"
author = "Anupam Chakraborty"
copyright = "2026, Anupam Chakraborty"
release = "0.2.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.githubpages",
]

autosummary_generate = True
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_class_signature = "separated"
autodoc_preserve_defaults = True

napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = False

templates_path = []
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "sphinx_rtd_theme"
html_title = "DORT Input Preparation API"
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_show_sourcelink = False
html_last_updated_fmt = "%d %b %Y"

html_theme_options = {
    "collapse_navigation": False,
    "navigation_depth": 3,
    "sticky_navigation": True,
    "titles_only": False,
    "style_external_links": True,
}

html_context = {
    "display_github": True,
    "github_user": "Anupam-IGC",
    "github_repo": "DORT_Input",
    "github_version": "main",
    "conf_py_path": "/docs/source/",
}

# In a network-restricted environment, build with:
#   DORT_DOCS_OFFLINE=1 make html
# to suppress external intersphinx downloads.
if os.environ.get("DORT_DOCS_OFFLINE") == "1":
    intersphinx_mapping = {}
else:
    intersphinx_mapping = {
        "python": ("https://docs.python.org/3", None),
        "numpy": ("https://numpy.org/doc/stable/", None),
        "matplotlib": ("https://matplotlib.org/stable/", None),
    }
    intersphinx_timeout = 5
