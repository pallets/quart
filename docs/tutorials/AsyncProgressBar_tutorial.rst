.. AsyncProgressBar_tutorial:

Tutorial: Asynchronous Progress Bar
===================================

This tutorial will guide you through building the example present in the
``examples/AsyncProgressBar`` directory. The nature of this example is to
demonstrate one way to handle a longer task within Quart, along with an
example of how to show the progress of that task, without blocking or
slowing down user interaction.

Running the example
'''''''''''''''''''

To run the example, in ``examples/AsyncProgressBar`` the following should
start the server, (see :ref:`installation` first),

.. code-block:: console

    $ export QUART_APP=progress_bar:app
    $ quart run

the example web app is then available at `http://localhost:5000/
<http://localhost:5000/>`_.

1: Redis
--------

This example uses Redis as a data store for keeping track of the state of our
long task. The description as found  on their site is as follows.

    ``Redis is an open source (BSD licensed), in-memory data structure store,
    used as a database, cache and message broker. It supports data structures
    such as strings, hashes, lists, sets, sorted sets with range queries,
    bitmaps, hyperloglogs and geospatial indexes with radius queries.
    Redis has built-in replication, Lua scripting, LRU eviction, transactions
    and different levels of on-disk persistence, and provides high
    availability via Redis Sentinel and automatic partitioning with Redis
    Cluster.``

More information can be found at `https://redis.io/ <https://redis.io/>`_.

Using Redis opens up a whole host of possible use cases which are beyond the
scope of this tutorial, but can include:

    - Interacting with information across multiple servers and / or applications
    - Atomic data operations to avoid race conditions
    - Real time analysis
    - Caching / Queueing
    - Storage of data along with a pre-defined Time To Live, which comes in
      handy for user sessions and auto log-out
    - more...

Redis is separate from Quart and does need to be installed to utilize it.
Instructions on how to do that can be found here `https://redis.io/download
<https://redis.io/download>`_.

2: Installation
---------------

It is always best to run python projects within a virtualenv, which should be
created and activated as follows,

.. code-block:: console

    $ cd AsyncProgressBar
    $ pipenv install quart aioredis redis

for this blog we will need Quart, aioredis, and redis libraries. Now
pipenv can be activated,

.. code-block:: console

    $ pipenv shell

3: Creating the app
-------------------

First we'll import the required libraries, and initialize the Quart web app object.

.. code-block:: python

    import asyncio
    import random
    import aioredis
    import redis
    from quart import Quart, request, url_for, jsonify

    app = Quart(__name__)

Then, for the purposes of this tutorial and so that you have a clean slate
each time you run the app, we'll create a synchronous connection to the Redis
database and run ``FLUSHDB`` to clear any data from the last execution.
In production, depending on what it is Redis and / or the app(s) are being
used for, this may not be desired behavior. Please modify where necessary.

.. code-block:: python

    sr = redis.StrictRedis(host='localhost', port=6379)
    sr.execute_command('FLUSHDB')

Let's define an asynchronous function to handle our work called ``some_work()``.

.. code-block:: python

    async def some_work():
        global aredis
        await aredis.set('state', 'running')
        work_to_do = range(1, 26)
        await aredis.set('length_of_work', len(work_to_do))
        for i in work_to_do:
            await aredis.set('processed', i)
            await asyncio.sleep(random.random())
        await aredis.set('state', 'ready')
        await aredis.set('percent', 100)

What we're doing here is setting the key ``state`` to ``running`` and then
using a for loop with ``random.random()`` to simulate work that may need to
be done. Once complete the ``state`` is returned to ``ready`` so that more
work can be queued and performed.

That's all well and good, but how do we access that from within the web
application? We'll cover that a bit later.

Next is the function to check the status of the work. This function returns
a JSON response, which is used by ``progress()`` below to generate the
progress bar.

.. code-block:: python

    @app.route('/check_status/')
    async def check_status():
        global aredis, sr
        status = dict()
        try:
            if await aredis.get('state') == b'running':
                if await aredis.get('processed') != await aredis.get('lastProcessed'):
                    await aredis.set('percent', round(
                        int(await aredis.get('processed')) / int(await aredis.get('length_of_work')) * 100, 2))
                    await aredis.set('lastProcessed', str(await aredis.get('processed')))
        except:
            pass

        try:
            status['state'] = sr.get('state').decode()
            status['processed'] = sr.get('processed').decode()
            status['length_of_work'] = sr.get('length_of_work').decode()
            status['percent_complete'] = sr.get('percent').decode()
        except:
            status['state'] = sr.get('state')
            status['processed'] = sr.get('processed')
            status['length_of_work'] = sr.get('length_of_work')
            status['percent_complete'] = sr.get('percent')

        status['hint'] = 'refresh me.'

        return jsonify(status)

in ``check_status()``, if the ``state`` is ``running`` then we'll retrieve
information on the progress, calculate a percentage, and throw it all into a
dictionary. That dictionary is then handed to ``jsonify()`` to return a JSON
response. The synchronous calls to Redis were added to work around an issue
where ``aredis`` did not exist yet.

Next is the function to display a progress bar, to visually represent where
we are in the work that is being done. This view / endpoint is just a page
which uses Javascript and JQuery to poll ``check_status()``, via AJAX, on an
interval of ``1000`` milliseconds, as long as the percentage is less than 100.
Each time the percentage changes, the bar and the text under the bar are
updated. When the percentage reaches 100, then the script displays "Done!".

.. code-block:: python

    @app.route('/progress/')
    async def progress():
        return """
        <!doctype html>
        <html lang="en">
        <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Asyncio Progress Bar Demo</title>
        <link rel="stylesheet" href="//code.jquery.com/ui/1.12.1/themes/base/jquery-ui.css">
        <link rel="stylesheet" href="/resources/demos/style.css">
        <script src="https://code.jquery.com/jquery-1.12.4.js"></script>
        <script src="https://code.jquery.com/ui/1.12.1/jquery-ui.js"></script>
        <script>
        var percent;

        function checkStatus() {
            $.getJSON('""" + url_for('check_status') + """', function (data) {
                console.log(data);
                percent = parseFloat(data.percent_complete);
                update_bar(percent);
                update_text(percent);
              });
            if (percent != 100) {
                setTimeout(checkStatus, 1000);
            }
        }

        function update_bar(val) {
            if (val.length <= 0) {
                val = 0;
            }
            $( "#progressBar" ).progressbar({
                value: val
            });
        };

        function update_text(val) {
            if (val != 100) {
                document.getElementById("progressData").innerHTML = "&nbsp;<center>"+percent+"%</center>";
            } else {
                document.getElementById("progressData").innerHTML = "&nbsp;<center>Done!</center>";
            }
        }

        checkStatus();
        </script>
        </head>
        <body>
        <center><h2>Progress of work is shown below</h2></center>
        <div id="progressBar"></div>
        <div id="progressData" name="progressData"><center></center></div>


        </body>
        </html>"""

Next is just a view for entering / interacting with the example, so the work
can be started. It starts the work by calling the ``start_work()`` function.

.. code-block:: python

    @app.route('/')
    async def index():
        return 'This is the index page. Try the following to <a href="' + url_for(
            'start_work') + '">start some test work</a> with a progress indicator.'

The ``start_work()`` function then gets the event loop, creates an
asynchronous connection to Redis. After that, if the current ``state`` is
``running``, it will advise you to wait for the current work to finish.
If the ``state`` is ``ready``, then it will add the ``some_work()`` function
to the event loop, and return an indication that the work has been started,
before redirecting the user to the ``/progress`` view.

.. code-block:: python

    @app.route('/start_work/')
    async def start_work():
        global aredis
        loop = asyncio.get_event_loop()
        aredis = await aioredis.create_redis('redis://localhost', loop=loop)

        if await aredis.get('state') == b'running':
            return "<center>Please wait for current work to finish.</center>"
        else:
            await aredis.set('state', 'ready')

        if await aredis.get('state') == b'ready':
            loop.create_task(some_work())
            body = '''
            <center>
            work started!
            </center>
            <script type="text/javascript">
                window.location = "''' + url_for('progress') + '''";
            </script>'''
            return body

Finally, we run the app.

.. code-block:: python

    if __name__ == "__main__":
        app.run('localhost', port=5000, debug=True)


Conclusion
----------

This wraps up the tutorial on performing asynchronous work withing a Quart
web application. This is but one way to accomplish the handling of a long
task without blocking the user interface.
