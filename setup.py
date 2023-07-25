from setuptools import setup, find_packages

# Read in requirements.txt
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='onshape-to-shaper',
    version='1.0.0',
    description='A Python package to convert Onshape drawings to Shaper tool format.',
    author='Darren Lynch',
    packages=find_packages(),
    install_requires=requirements,
)
