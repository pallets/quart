import asyncio
import random
import aioredis
import redis
from quart import Quart, request, url_for, jsonify

app = Quart(__name__)

sr = redis.StrictRedis(host='localhost', port=6379)
sr.execute_command('FLUSHDB')


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


@app.route('/')
async def index():
    return 'This is the index page. Try the following to <a href="' + url_for(
        'start_work') + '">start some test work</a> with a progress indicator.'


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


if __name__ == "__main__":
    app.run('localhost', port=5000, debug=True)
