#!/usr/bin/env python3
"""
Simple tools used in various places across this package.
"""
import re
import time
import numpy as np
import functools
import warnings
import matplotlib as mpl
from numbers import Number, Integral
rcParams = mpl.rcParams
try:
    from icecream import ic
except ImportError:  # graceful fallback if IceCream isn't installed
    ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a) # noqa
__all__ = ['arange', 'edges', 'edges2d', 'units']

# Change this to turn on benchmarking
BENCHMARK = False

# Benchmarking tools for developers
class _benchmark(object):
    """Timer object that can be used to time things."""
    def __init__(self, message):
        self.message = message
    def __enter__(self):
        self.time = time.clock()
    def __exit__(self, *args):
        if BENCHMARK:
            print(f'{self.message}: {time.clock() - self.time}s')

def _logger(func):
    """A decorator that logs the activity of the script (it actually just prints it,
    but it could be logging!). See: https://stackoverflow.com/a/1594484/4970632"""
    @functools.wraps(func)
    def decorator(*args, **kwargs):
        res = func(*args, **kwargs)
        if BENCHMARK:
            print(f'{func.__name__} called with: {args} {kwargs}')
        return res
    return decorator

def _timer(func):
    """A decorator that prints the time a function takes to execute.
    See: https://stackoverflow.com/a/1594484/4970632"""
    @functools.wraps(func)
    def decorator(*args, **kwargs):
        if BENCHMARK:
            t = time.clock()
        res = func(*args, **kwargs)
        if BENCHMARK:
            print(f'{func.__name__}() time: {time.clock()-t}s')
        return res
    return decorator

def _counter(func):
    """A decorator that counts and prints the cumulative time a function
    has benn running. See: https://stackoverflow.com/a/1594484/4970632"""
    @functools.wraps(func)
    def decorator(*args, **kwargs):
        if BENCHMARK:
            t = time.clock()
        res = func(*args, **kwargs)
        if BENCHMARK:
            decorator.time += (time.clock() - t)
            decorator.count += 1
            print(f'{func.__name__}() cumulative time: {decorator.time}s ({decorator.count} calls)')
        return res
    decorator.time = 0
    decorator.count = 0 # initialize
    return decorator

# Important private helper func
def _notNone(*args, names=None):
    """Returns the first non-``None`` value, used with keyword arg aliases and
    for setting default values. Ugly name but clear purpose. Pass the `names`
    keyword arg to issue warning if multiple args were passed. Must be list
    of non-empty strings."""
    if names is None:
        for arg in args:
            if arg is not None:
                return arg
        return arg # last one
    else:
        first = None
        kwargs = {}
        if len(names) != len(args) - 1:
            raise ValueError(f'Need {len(args)+1} names for {len(args)} args, but got {len(names)} names.')
        names = [*names, '']
        for name,arg in zip(names,args):
            if arg is not None:
                if first is None:
                    first = arg
                if name:
                    kwargs[name] = arg
        if len(kwargs)>1:
            warnings.warn(f'Got conflicting or duplicate keyword args, using the first one: {kwargs}')
        return first

# Accessible for user
def arange(min_, *args):
    """Identical to `numpy.arange`, but with inclusive endpoints. For
    example, ``plot.arange(2,4)`` returns ``np.array([2,3,4])`` instead
    of ``np.array([2,3])``."""
    # Optional arguments just like np.arange
    if len(args) == 0:
        max_ = min_
        min_ = 0
        step = 1
    elif len(args) == 1:
        max_ = args[0]
        step = 1
    elif len(args) == 2:
        max_ = args[0]
        step = args[1]
    else:
        raise ValueError('Function takes from one to three arguments.')
    # All input is integer
    if all(isinstance(val,Integral) for val in (min_,max_,step)):
        min_, max_, step = np.int64(min_), np.int64(max_), np.int64(step)
        max_ += 1
    # Input is float or mixed, cast to float64
    # Don't use np.nextafter with np.finfo(np.dtype(np.float64)).max, because
    # round-off errors from continually adding step to min mess this up
    else:
        min_, max_, step = np.float64(min_), np.float64(max_), np.float64(step)
        max_ += step/2
    return np.arange(min_, max_, step)

def edges(array, axis=-1):
    """
    Calculates approximate "edge" values given "center" values. This is used
    internally to calculate graitule edges when you supply centers to
    `~matplotlib.axes.Axes.pcolor` or `~matplotlib.axes.Axes.pcolormesh`, and
    in a few other places.

    Parameters
    ----------
    array : array-like
        Array of any shape or size. Generally, should be monotonically
        increasing or decreasing along `axis`.
    axis : int, optional
        The axis along which "edges" are calculated. The size of this axis
        will be augmented by one.

    Returns
    -------
    `~numpy.ndarray`
        Array of "edge" coordinates.
    """
    # First permute
    array = np.array(array)
    array = np.swapaxes(array, axis, -1)
    # Next operate
    array = np.concatenate((
        array[...,:1]  - (array[...,1]-array[...,0])/2,
        (array[...,1:] + array[...,:-1])/2,
        array[...,-1:] + (array[...,-1]-array[...,-2])/2,
        ), axis=-1)
    # Permute back and return
    array = np.swapaxes(array, axis, -1)
    return array

def edges2d(z):
    """
    Like :func:`edges` but for 2D arrays.
    The size of both axes are increased of one.

    Parameters
    ----------
    array : array-like
        Two-dimensional array.

    Returns
    -------
    `~numpy.ndarray`
        Array of "edge" coordinates.
    """
    z = np.asarray(z)
    ny, nx = z.shape
    zzb = np.zeros((ny+1, nx+1))

    # Inner
    zzb[1:-1, 1:-1] = 0.25 * (z[1:, 1:] + z[:-1, 1:] +
                              z[1:, :-1] + z[:-1, :-1])
    # Lower and upper
    zzb[0] += edges(1.5*z[0]-0.5*z[1])
    zzb[-1] += edges(1.5*z[-1]-0.5*z[-2])

    # Left and right
    zzb[:, 0] += edges(1.5*z[:, 0]-0.5*z[:, 1])
    zzb[:, -1] += edges(1.5*z[:, -1]-0.5*z[:, -2])

    # Corners
    zzb[[0, 0, -1, -1], [0, -1, -1, 0]] *= 0.5

    return zzb

def units(value, numeric='in'):
    """
    Flexible units -- this function is used internally all over ProPlot, so
    that you don't have to use "inches" or "points" for all sizing arguments.
    See `this link <http://iamvdo.me/en/blog/css-font-metrics-line-height-and-vertical-align#lets-talk-about-font-size-first>`_
    for info on the em square units.

    Parameters
    ----------
    value : float or str or list thereof
        A size "unit" or *list thereof*. If numeric, assumed unit is `numeric`.
        If string, we look for the format ``'123.456unit'``, where the
        number is the value and ``'unit'`` is one of the following.

        ======  ===================================================================
        Key     Description
        ======  ===================================================================
        ``m``   Meters
        ``cm``  Centimeters
        ``mm``  Millimeters
        ``ft``  Feet
        ``in``  Inches
        ``pt``  Points (1/72 inches)
        ``px``  Pixels on screen, uses dpi of ``rc['figure.dpi']``
        ``pp``  Pixels once printed, uses dpi of ``rc['savefig.dpi']``
        ``em``  Em-square for ``rc['font.size']``
        ``ex``  Ex-square for ``rc['font.size']``
        ``Em``  Em-square for ``rc['axes.titlesize']``
        ``Ex``  Ex-square for ``rc['axes.titlesize']``
        ======  ===================================================================

    numeric : str, optional
        The assumed unit for numeric arguments, and the output unit. Default
        is **inches**, i.e. ``'in'``.
    """
    # Loop through arbitrary list, or return None if input was None (this
    # is the exception).
    if not np.iterable(value) or isinstance(value, str):
        singleton = True
        values = (value,)
    else:
        singleton = False
        values = value

    # Font unit scales
    # NOTE: Delay font_manager import, because want to avoid rebuilding font
    # cache, which means import must come after TTFPATH added to environ,
    # i.e. inside styletools.register_fonts()!
    small = rcParams['font.size'] # must be absolute
    large = rcParams['axes.titlesize']
    if isinstance(large, str):
        import matplotlib.font_manager as mfonts
        scale = mfonts.font_scalings.get(large, 1) # error will be raised somewhere else if string name is invalid!
        large = small*scale

    # Dict of possible units
    unit_dict = {
        # Physical units
        'in': 1.0, # already in inches
        'm':  39.37,
        'ft': 12.0,
        'cm': 0.3937,
        'mm': 0.03937,
        'pt': 1/72.0,
        # Font units
        'em': small/72.0,
        'ex': 0.5*small/72.0, # more or less; see URL
        'Em': large/72.0, # for large text
        'Ex': 0.5*large/72.0,
        }
    # Display units
    # WARNING: In ipython shell these take the value 'figure'
    if not isinstance(rcParams['figure.dpi'], str):
        unit_dict['px'] = 1/rcParams['figure.dpi'] # on screen
    if not isinstance(rcParams['savefig.dpi'], str):
        unit_dict['pp'] = 1/rcParams['savefig.dpi'] # once 'printed', i.e. saved

    # Iterate
    try:
        scale = unit_dict[numeric]
    except KeyError:
        raise ValueError(f'Invalid numeric unit {numeric}. Valid units are {", ".join(unit_dict.keys())}.')
    result = []
    for value in values:
        if value is None or isinstance(value, Number):
            result.append(value)
            continue
        elif not isinstance(value, str):
            raise ValueError(f'Size spec must be string or number or list thereof, received {values}.')
        regex = re.match('^([-+]?[0-9.]*)(.*)$', value)
        num, unit = regex.groups()
        try:
            result.append(float(num)*unit_dict[unit]/scale)
        except (KeyError, ValueError):
            raise ValueError(f'Invalid size spec {value}. Valid units are {", ".join(unit_dict.keys())}.')
    if singleton:
        result = result[0]
    return result

