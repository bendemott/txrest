"""
To install from source::

    # change to the directory where this setup.py is located.
    sudo python setup.py install
    
To install from pypi::

    sudo pip install txrest
    
**To upload to PyPi**:
    https://hynek.me/articles/sharing-your-labor-of-love-pypi-quick-and-dirty/
    Create a file named ``.pypirc`` with the contents::
    
        [distutils]
        index-servers=
            pypi
            test

        [test]
        repository = https://testpypi.python.org/pypi
        username = <your test user name goes here>
        password = <your test password goes here>

        [pypi]
        repository = https://pypi.python.org/pypi
        username = <your production user name goes here>
        password = <your production password goes here>
"""

try:
    # setuptools first, because it provides "developer"
    # functionality
    from setuptools import setup
except ImportError:
    sys.stdout.write(
        os.linesep
        + 'NOTE: for --develop flag support execute '
        + '`pip install setuptools` and run again'
        + os.linesep)
    try:
        from distutils import setup
    except ImportError:
        from distutils.core import setup
    
setup(
    name='txrest',
    url='https://github.com/bendemott/txrest.git',
    #test_suite="nose.collector", # TODO !!!
    license='MIT',
    version='0.6.2',
    packages=['txrest'],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Programming Language :: Python",
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers"
    ],
)
