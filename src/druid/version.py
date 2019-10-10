from pkg_resources import get_distribution, DistributionNotFound


try:
    __version__ = get_distribution('monome-druid').version
except DistributionNotFound:
    __version__ = '<unknown>'
