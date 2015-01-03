from setuptools import setup

setup(name='NPC360 SMSIO',
      version='1.0',
      description='SMS IO controller for NPC360',
      author='NPC360',
      author_email='NPC360@foo.bar',
      url='http://foo.bar',
      install_requires=['Flask>=0.7.2', 'requests', 'twilio','datetime','logging','os', 'tinydb', 'sqlalchemy' ],
     )
