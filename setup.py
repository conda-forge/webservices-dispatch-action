from setuptools import setup, find_packages

setup(
    name="webservices_dispatch_action",
    version="0.1",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'run-webservices-dispatch-action=webservices_dispatch_action.__main__:main',
        ],
    },
)
