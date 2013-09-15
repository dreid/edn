from setuptools import setup


setup(
    name='edn',
    version='0.0.1',
    packages=['edn'],
    package_data={'edn': ['edn.parsley']},
    install_requires=[
        'parsley>=1.1pre1',
        'pytz',
    ],
)
