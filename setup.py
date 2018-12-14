from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand
import io
import codecs
import os
import sys

import koppercoin

here = os.path.abspath(os.path.dirname(__file__))

def read(*filenames, **kwargs):
    encoding = kwargs.get('encoding', 'utf-8')
    sep = kwargs.get('sep', '\n')
    buf = []
    for filename in filenames:
        with io.open(filename, encoding=encoding) as f:
            buf.append(f.read())
    return sep.join(buf)

long_description = read('README.md')

setup(
    name='koppercoin',
    version=koppercoin.__version__,
    # url='',
    # license='',
    author='Henning Kopp, David Moedinger',
    install_requires=['pypbc',
                    'pycrypto>=2.6.1',
                    'gmpy',
                    'crochet',
                    'twisted',
                    'pynacl',
                    ],
    dependency_links=['https://github.com/debatem1/pypbc/archive/master.zip#egg=pypbc'],
    author_email='henning.kopp@uni-ulm.de, david.moedinger@uni-ulm.de',
    description='A distributed decentralized storage system with integrated privacy-preserving payments',
    long_description=long_description,
    packages=['koppercoin'],
    include_package_data=True,
    platforms='any',
    # test_suite='sandman.test.test_sandman',
    # classifiers = [
    #     'Programming Language :: Python',
    #     'Natural Language :: English',
    #     ],
    # keywords = '',
    extras_require={
        'testing': ['pandas', 'matplotlib','nose','nose-cov', 'pympler'],
    }
)
