.. _design_choices::

Design Choices
==============

The asyncio callback ``create_server`` approach is faster than the
streaming ``start_server`` approach, and hence is used. This is based
on benchmarking and the `uvloop
<https://github.com/MagicStack/uvloop>`_ research.
