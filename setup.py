from setuptools import setup


setup(
    name='edn',
    version='0.0.1',
    packages=['edn'],
    package_data={'edn': ['edn.parsley']},
    install_requires=[
        'iso8601>=0.1.6',
        'parsley>=1.2',
        'perfidy',
    ],
)
