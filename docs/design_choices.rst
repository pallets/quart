.. _design_choices::

Design Choices
==============

Coroutines or functions
-----------------------

It is quite easy to call sync and trigger async execution from a
coroutine and hard to trigger async execution from a function, see
async_compatibility_. For this reason coroutines are preferred even in
cases where IO seems unlikely.
