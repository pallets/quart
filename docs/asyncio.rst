.. _asyncio:

Asyncio
=======

Asyncio is the part of the Python standard library that provides an
event loop with IO (input/output) operations. It exists to allow
concurrent programming in Python, whereby the event loop switches to
another task whilst the previous task waits on IO. This concurrency
allows for greater CPU utilisation and hence greater throughput
performance.

The easiest way to understand this is to consider something concrete,
namely a demonstrative simulation In the following we fetch a url with
a simulated IO delay,

.. code-block:: python

    import asyncio


    async def simulated_fetch(url, delay):
        await asyncio.sleep(delay)
        print(f"Fetched {url} after {delay}")
        return f"<html>{url}"


    def main():
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(asyncio.gather(
            simulated_fetch('http://google.com', 2),
            simulated_fetch('http://bbc.co.uk', 1),
        ))
        print(results)

you should see the following output,

>>> Fetched http://bbc.co.uk after 1
>>> Fetched http://google.com after 2
>>> ['<html>http://google.com', '<html>http://bbc.co.uk']

which indicates that despite calling the ``google.com`` fetch first,
the ``bbc.co.uk`` actually completed first i.e. the code ran
concurrently. Additionally the code runs in a little over 2 seconds
rather than over 3 as expected with synchronous code.

Relevance to web servers
------------------------

Web servers by definition do IO, in that they receive and respond to
requests from the network. This means that asyncio is a very good fit
even if the code within the framework does no IO itself. Yet in
practice IO is present, for example when loading a template from a
file, or contacting a database or another server.
