from setuptools import find_packages, setup

setup(
    name='jellypy_pyCIPAPI',
    version='0.1.0',
    author="NHS Bioinformatics Group",
    author_email="joowook.ahn@nhs.net",
    description='Python library for access the GELs CPI API',
    license="TBC",
    url='https://github.com/NHS-NGS/JellyPy',
    packages=find_packages(),
    install_requires=[
        'docopt == 0.6.2',
        'GelReportModels == 7.2.10',
        'maya == 0.6.1',
        'PyJWT == 1.7.1',
        'requests == 2.22.0',
        'pandas == 0.25.1',
        'openpyxl == 2.6.3'
    ]
)
