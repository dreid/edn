from setuptools import setup


setup(
    name='edn',
    version='0.0.1',
    packages=['edn'],
    package_data={'edn': ['edn.parsley']},
    install_requires=[
        # iso8601 0.1.5 introduces a timezone parsing bug.
        # https://bitbucket.org/micktwomey/pyiso8601/issue/8/015-parses-negative-timezones-incorrectly
        'iso8601==0.1.4',
        'parsley>=1.2',
        'perfidy',
    ],
)
