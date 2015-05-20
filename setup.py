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
    version='0.5.1',
    packages=['txrest'],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers"
    ],
)
