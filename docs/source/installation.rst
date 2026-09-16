Installation
============

Requirements
------------

Python 3.10 or newer is recommended.

The runtime dependencies are currently:

* NumPy;
* Matplotlib;
* pandas — spreadsheet mixture-table import;
* openpyxl — Excel ``.xlsx`` reader used by pandas.

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

   python examples/comprehensive_mixture_spreadsheet.py

Spreadsheet mixture input
-------------------------

The example workbook is under ``examples/data/mixtures_example.xlsx``.  A
normal project may keep its own workbook anywhere and pass the path to
``model.load_mixtures_from_excel(...)`` or ``model.prepare_mixtures_from_excel(...)``.

Documentation dependencies
--------------------------

Install the documentation requirements with:

.. code-block:: bash

   pip install -r docs/requirements.txt

Build the documentation locally:

.. code-block:: bash

   cd docs
   make html

Behind a restricted proxy, use:

.. code-block:: bash

   DORT_DOCS_OFFLINE=1 make html

The generated site is under ``docs/build/html/index.html``.
