import pathlib
from setuptools import find_packages, setup

README = ( pathlib.Path(__file__).parent / 'readme.md').read_text()

setup(
    name='jellypy_pyCIPAPI',
    version='0.1.0',
    author="NHS Bioinformatics Group",
    author_email="joowook.ahn@nhs.net",
    description='Python client library the Genomics England CIPAPI',
    url='https://github.com/NHS-NGS/JellyPy/pyCIPAPI',
    packages=find_packages(),
    python_requires='>=3.6.*',
    long_description=README,
    long_description_content_type="text/markdown",
    install_requires=[
        'docopt == 0.6.2',
        'GelReportModels == 7.2.10',
        'maya == 0.6.1',
        'PyJWT == 1.7.1',
        'requests == 2.22.0',
        'pandas == 0.25.1',
        'openpyxl == 2.6.3'
    ],
    classifiers=[
        "Programming Language :: Python :: 3.6"
    ],
    include_package_data=True
)