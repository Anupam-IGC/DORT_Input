Installation
============

Requirements
------------

Python 3.10 or newer is required. NumPy, Matplotlib, pandas, and openpyxl are
installed automatically when package dependencies can be obtained.

Install the wheel
-----------------

For normal use, install the supplied wheel:

.. code-block:: bash

   python -m pip install dort_input-0.4.1-py3-none-any.whl

Install the source package
--------------------------

After extracting the source ZIP, open a terminal in the ``DORT_Input`` folder:

.. code-block:: bash

   python -m pip install .

Use an editable installation while changing examples or package code:

.. code-block:: bash

   python -m pip install -e ".[test,docs]"

Verify the installation
-----------------------

.. code-block:: bash

   python -c "from dort_input import DORTModel; print('DORT package ready')"
   dort-mixture --help

Then run the first tutorial from the source repository:

.. code-block:: bash

   python examples/modeling_basics.py

Network-restricted computers
----------------------------

The wheel contains the DORT input-preparation code but not its third-party
dependencies. On an offline computer, install compatible NumPy, Matplotlib,
pandas, and openpyxl wheels first, then install ``dort-input`` with:

.. code-block:: bash

   python -m pip install --no-deps dort_input-0.4.1-py3-none-any.whl

The package does not bundle the DORT executable, the microscopic cross-section
library, or the external ``m_ia_oa.for`` mixer.
