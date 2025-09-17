from setuptools import setup, find_packages

# Read requirements.txt to populate install_requires
with open('requirements.txt', 'r') as f:
    requires = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name='zclonic',
    version='0.1.0',
    description='Zclonic - Enterprise Research AI Portal',
    author='AtonixDev',
    packages=find_packages(exclude=('tests', 'ci')),
    include_package_data=True,
    install_requires=requires,
    python_requires='>=3.11',
    entry_points={
        'console_scripts': [
            'zclonic-run = run:app',
        ],
    },
)
