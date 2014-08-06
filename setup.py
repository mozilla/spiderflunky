import sys

# Prevent spurious errors during `python setup.py test`, a la
# http://www.eby-sarna.com/pipermail/peak/2010-May/003357.html:
try:
    import multiprocessing
except ImportError:
    pass

from setuptools import setup, find_packages


setup(
    name='spiderflunky',
    version='0.1',
    description='Static analysis for JavaScript',
    long_description=open('README.rst').read(),
    author='Erik Rose',
    author_email='erik@mozilla.com',
    license='MPL',
    packages=find_packages(exclude=['ez_setup']),
    install_requires=['more_itertools>=2.1', 'toposort>=1.0', 'networkx', 'funcy'],
    tests_require=['nose'],
    test_suite='nose.collector',
    url='https://github.com/erikrose/spiderflunky',
    include_package_data=True,
    classifiers=[
        'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7'
        ],
    keywords=['static analysis', 'javascript', 'js', 'parser', 'alias analysis']
)
