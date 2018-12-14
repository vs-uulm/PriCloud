What is PriCloud?
=================

PriCloud is a research project to create a privacy preserving file storage using a blockchain. 

More information can be found here:

 * https://www.uni-ulm.de/in/vs/res/proj/pricloud/
 * https://ieeexplore.ieee.org/abstract/document/7966965


Installation Instructions
=========================

We need pbc (0.5.14) which in turn requires the gmp library.
Unfortunately this needs to be installed manually.
The koppercoin package can be installed with ``python setup.py install``.
Additional packages needed for the evaluation script can be installed
with ``pip3 install -e ".[testing]" --verbose``

LibPBC by default installs itself into ``/usr/local/lib``. This can
lead to problems on systems where this is not in the search path of
the dynamic linker. In this case please add ``export
LD_LIBRARY_PATH=/usr/local/lib`` to your ~/.bashrc.

You can run the tests with ``nosetests --with-doctest --verbose
`` or alternatively ``python3 -m "nose" --with-doctest --verbose``.

Requirements
============
- Python 3
- pycrypto
- sphinx (only necessary if you want to generate the docs)
- pbc (0.5.14) which in turn requires the gmp library
