#!/bin/sh
# This script sets up a virtual environment for python3 for
# development
echo "Setting up virtual environment for Python 3"
#pyvenv venv
#. venv/bin/activate
pip3 install --upgrade pip
#install python dependencies and development tools
pip3 install ipython flake8 nose nose-cov jsonpickle sphinx

#install pbc
mkdir -p koppercoin/lib &&
cd koppercoin/lib
wget https://crypto.stanford.edu/pbc/files/pbc-0.5.14.tar.gz &&
tar xzvf pbc-0.5.14.tar.gz &&
cd pbc-0.5.14 &&
./configure && make
