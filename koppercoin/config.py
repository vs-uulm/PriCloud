# is this a testing environment?
test = False

import os

"""
The koppercoin base path
/<here>
-> koppercoin
    -> tokens
    -> util
    ...
"""
koppercoin_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
save_path = koppercoin_path