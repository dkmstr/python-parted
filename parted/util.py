# Copyright (c) 2023 Adolfo Gómez
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""
Utilities for parted

Author: Adolfo Gómez, dkmaster at dkmon dot com
"""
import typing
import os
import functools
import logging

from . import exceptions

logger = logging.getLogger(__name__)

T = typing.TypeVar('T')


# class Getter(type):
#    def __getitem__(self: typing.Any, item: typing.Any):
#        if hasattr(self, '_getter'):
#            return getattr(self, '_getter')(item)
#        raise NotImplementedError

# Decorator that ensures the attribute "attr" is present and it's bool evaluates to "True" before calling the method
def ensure_valid(attr: str) -> typing.Callable:
    """Ensures the attribute "attr" is present and it's bool evaluates to "True" before calling the method.
    
    If the attribute is not present or it's bool evaluates to "False", an ``exceptions.InvalidObjectException`` is raised.

    Args:
        attr (str): _description_

    Returns:
        typing.Callable: _description_
    """
    def decorator(func: typing.Callable) -> typing.Callable:
        @functools.wraps(func)
        def wrapper(
            self: typing.Any, *args: typing.Any, **kwargs: typing.Any
        ) -> typing.Any:
            if not hasattr(self, attr) or not getattr(self, attr):
                raise exceptions.InvalidObjectError(
                    f"Invalid object: {attr} is not valid"
                )
            return func(self, *args, **kwargs)

        return wrapper

    return decorator
    

# Basic decorator to ensure obj is present and is a valid object
ensure_obj = ensure_valid('obj')

# Decorator similar to ensure_valid, but returns a default value instead of raising an exception
def ensure_valid_or_default(attr: str, default: typing.Any) -> typing.Callable:
    """
    Decorator similar to ensure_valid, but returns a default value instead of raising an exception

    Args:
        attr (str): Attribute to check
        default (typing.Any): Default value to return if attr is not valid

    Returns:
        typing.Callable: Decorator
    """
    def decorator(func: typing.Callable) -> typing.Callable:
        @functools.wraps(func)
        def wrapper(
            self: typing.Any, *args: typing.Any, **kwargs: typing.Any
        ) -> typing.Any:
            if not hasattr(self, attr) or not getattr(self, attr):
                # if default is callable, call it
                if callable(default):
                    return default()
                return default
            return func(self, *args, **kwargs)

        return wrapper

    return decorator

# Partial to ensure a class method returns a default is its object is not valid
# Used on properties
ensure_obj_or_default = functools.partial(ensure_valid_or_default, 'obj')

# Decorator that ensures effective process user is root
def ensure_root(func: typing.Callable) -> typing.Callable:
    """
    Decorator that ensures effective process user is root

    Args:
        func (typing.Callable): Function to decorate

    Raises:
        exceptions.PartedException: If effective user is not root

    Returns:
        typing.Callable: _description_
    """
    @functools.wraps(func)
    def wrapper(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        if os.geteuid() != 0:
            raise exceptions.PartedException("You must be root to perform this operation")
        return func(*args, **kwargs)

    return wrapper

# Decorator to cache result of a method or property on an specific class attribute
def cache_on(attr: str) -> typing.Callable:
    """
    Decorator to cache result of a method or property on an specific class attribute

    Args:
        attr (str): Attribute to cache on
    
    Returns:
        typing.Callable: Decorator
    """
    # prepend _ to attr to avoid conflicts
    attr = f'_{attr}'
    def decorator(func: typing.Callable) -> typing.Callable:
        @functools.wraps(func)
        def wrapper(self: typing.Any, *args: typing.Any, **kwargs: typing.Any) -> typing.Any:
            if not hasattr(self, attr):
                setattr(self, attr, func(self, *args, **kwargs))
            return getattr(self, attr)

        return wrapper

    return decorator

def cache_del(obj: typing.Any, attr: str) -> None:
    """
    Cleans cache of a method or property on an specific class attribute

    Args:
        obj (typing.Any): Object to clean cache on
        attr (str): Attribute to clean
    """
    attr = f'_{attr}'
    if hasattr(obj, attr):
        delattr(obj, attr)

def cache_set(obj: typing.Any, attr: str, value: typing.Any) -> None:
    """
    Updates cache of a method or property on an specific class attribute

    Args:
        obj (typing.Any): Object to clean cache on
        attr (str): Attribute to clean
        value (typing.Any): Value to set
    """
    attr = f'_{attr}'
    setattr(obj, attr, value)

def make_destroyable(obj: T) -> T:
    """
    Checks if a object has a "_destroyable" attribute and sets it to True

    Args:
        obj (T): Object to check

    Returns:
        T: The same object
    """
    if hasattr(obj, '_destroyable'):
        setattr(obj, '_destroyable', True)
    else:
        logger.warning(f"Object {obj} is not destroyable and make_destroyable was called")
    return obj


class OpenContext:
    """Context manager for opening and closing after use"""
    _obj: typing.Any

    def __init__(self, object: typing.Any) -> None:
        self._obj = object

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._obj.close()
