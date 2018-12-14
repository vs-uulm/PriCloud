

class UI():
    """
    This class manages the UI. It provides some helpful functions
    which a user may need for interacting with the system.
    This is a class and not a namespace, since we need to store the
    wallet and whether we are mining.
    """

    def __init__(self, controler):
        # load the wallet
        self.controler = controler

    def get_balance(self):
        """
        This function returns the balance.
        """
        return self.controler.wallet.get_balance()

    def get_address(self):
        """
        This function returns our own address.
        """
        return self.controler.wallet.public_key

    def transfer(addr_amnt):
        """
        Transfers money to other addresses.
        :param addr_amnt: a list of pairs [(addr1, amnt1), ..., (addrn, amntn)]
            such that the i-th amount is sent to the i-th address.
        """
        raise NotImplementedError
