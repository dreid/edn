from setuptools import setup


setup(
    name='edn',
    version='0.0.1',
    packages=['edn'],
    package_data={'edn': ['edn.parsley']},
    install_requires=[
        'iso8601',
        'parsley>=1.1pre1',
        'perfidy',
    ],
)
