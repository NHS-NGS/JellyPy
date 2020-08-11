import pathlib
from setuptools import find_packages, setup

README = ( pathlib.Path(__file__).parent / 'pypi_readme.md').read_text()

setup(
    name='jellypy_tierup',
    version='0.3.1',
    author="NHS Bioinformatics Group",
    author_email="nana.mensah1@nhs.net",
    description='Reanalyse Tier 3 variants',
    license="MIT",
    url='https://github.com/NHS-NGS/JellyPy/tierup',
    packages=find_packages(),
    python_requires='>=3.6.*',
    long_description=README,
    long_description_content_type="text/markdown",
    package_data={'':['data/*.schema']},
    install_requires=[
        'click==7.0',
        'jsonschema==3.2.0',
        'jellypy-pyCIPAPI==0.2.3'
    ],
    entry_points = {
        'console_scripts': 'tierup=jellypy.tierup.interface:cli'
    },
    classifiers=[
        "Programming Language :: Python :: 3.6"
    ],
    include_package_data=True
)
