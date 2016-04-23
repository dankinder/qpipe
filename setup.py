from distutils.core import setup

version = '0.4'
setup(
  name = 'qpipe',
  packages = ['qpipe'],
  version = version,
  description = 'Quick and simple pipeline/flow-based multiprocessing',
  author = 'Dan Kinder',
  author_email = 'dkinder.is.me@gmail.com',
  url = 'https://github.com/dankinder/qpipe',
  download_url = 'https://github.com/dankinder/qpipe/tarball/' + version,
  keywords = ['multiprocessing', 'threading', 'pipeline', 'flow', 'pipe'],
  classifiers = [],
)
