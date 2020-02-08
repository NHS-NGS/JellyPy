import pathlib
from setuptools import find_packages, setup

README = ( pathlib.Path(__file__).parent / 'readme.md').read_text()

setup(
    name='jellypy_tierup',
    version='0.1.1',
    author="NHS Bioinformatics Group",
    author_email="nana.mensah1@nhs.net",
    description='Find GeL Tier 3 variants with Green PanelApp genes',
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
        'jellypy-pyCIPAPI==0.1.0'
    ],
    entry_points = {
        'console_scripts': 'tierup=jellypy.tierup.interface:cli'
    },
    classifiers=[
        "Programming Language :: Python :: 3.6"
    ],
    include_package_data=True
)
