document.addEventListener('DOMContentLoaded', function() {
    var es = new EventSource('/sse');
    es.onmessage = function (event) {
        var messages_dom = document.getElementsByTagName('ul')[0];
        var message_dom = document.createElement('li');
        var content_dom = document.createTextNode('Received: ' + event.data);
        message_dom.appendChild(content_dom);
        messages_dom.appendChild(message_dom);
    };

    document.getElementById('send').onclick = function() {
        fetch('/', {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify ({
                message: document.getElementsByName("message")[0].value,
            }),
        });
        document.getElementsByName("message")[0].value = "";
    };
});
