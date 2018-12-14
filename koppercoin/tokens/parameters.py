"""This file contains some parameters"""

def mining_reward_per_blockheight(blockheight):
    """Given a blockheight, this returns the amount that is contained
    in a valid coinbase-tx at that blockheight.
    """
    # the initial mining reward
    start = 2**40
    # we halve the generated tokens every 2**16 blocks
    halving_period = 2**16
    # how many halving have occurred up to the current block
    num_halvings_to_blockheight = blockheight // halving_period
    if num_halvings_to_blockheight >= 40:
        return 0
    else:
        return int((start) * (1/2)**num_halvings_to_blockheight)
