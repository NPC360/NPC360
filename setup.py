from setuptools import setup

setup(name='NPC360',
      version='1.0',
      description='NPC360 engine',
      author='NPC360',
      author_email='NPC360@foo.bar',
      url='http://foo.bar',
      install_requires=['Flask>=0.7.2', 'requests', 'json', 'twilio','datetime','logging','os', 'sqlalchemy', 'random', 'iron_worker', 'python-firebase' ],
     )
