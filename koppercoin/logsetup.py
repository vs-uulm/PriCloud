import logging
import logging.config
import json

config_dict = {
    'handlers': {
        'koppercoin.tokens.modelHandler': {'class': 'logging.FileHandler',
                                           'level': 'DEBUG',
                                           'formatter': 'simpleFormatter',
                                           'filename': 'tokens.model.log'},
        'koppercoin.tokens.walletHandler': {'class': 'logging.FileHandler',
                                            'level': 'DEBUG',
                                            'formatter': 'simpleFormatter',
                                            'filename': 'tokens.wallet.log'},
        'consoleHandler': {'class': 'logging.StreamHandler',
                           'level': 'DEBUG',
                           'formatter': 'simpleFormatter',
                           'stream': 'ext://sys.stdout'}},
    'formatters': {
        'simpleFormatter': {'class': 'logging.Formatter',
                            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'}},
    'loggers': {
        'logger_koppercoin.tokens.model': {'handlers': ['koppercoin.tokens.modelHandler'],
                                           'level': 'DEBUG'},
        'logger_koppercoin.tokens.wallet': {'handlers': ['koppercoin.tokens.walletHandler'],
                                            'level': 'DEBUG'},
        'root': {'handlers': ['consoleHandler']}},
    'version': 1
}

logging.config.dictConfig(config_dict)
