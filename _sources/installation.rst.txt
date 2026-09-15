Installation
============

Requirements
------------

Python 3.10 or newer is recommended.

The runtime dependencies are currently:

* NumPy
* Matplotlib

Install the repository requirements with:

.. code-block:: bash

   pip install -r requirements.txt

Current import model
--------------------

The repository is not yet packaged as an installable Python distribution.
Run scripts from the repository root, or otherwise ensure that the repository
root is on ``PYTHONPATH``.

For example:

.. code-block:: bash

   python examples/basic_model.py

Documentation dependencies
--------------------------

Install the documentation requirements with:

.. code-block:: bash

   pip install -r docs/requirements.txt

Build the documentation locally:

.. code-block:: bash

   cd docs
   make html

On Windows:

.. code-block:: bat

   cd docs
   make.bat html

The generated site will be available under:

.. code-block:: text

   docs/build/html/index.html

Read the Docs
-------------

The repository root contains ``.readthedocs.yaml``. After importing the
repository into Read the Docs, builds can be triggered automatically by
commits pushed to GitHub.
