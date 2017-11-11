.. _design_choices::

Design Choices
==============

Callbacks or streaming
----------------------

The asyncio callback ``create_server`` approach is faster than the
streaming ``start_server`` approach, and hence is used. This is based
on benchmarking and the `uvloop
<https://github.com/MagicStack/uvloop>`_ research.

Coroutines or functions
-----------------------

It is quite easy to call sync and trigger async execution from a
coroutine and hard to trigger async execution from a function, see
async_compatibility_. For this reason coroutines are prefered even in
cases where IO seems unlikely.
