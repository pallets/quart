document.addEventListener('DOMContentLoaded', function() {
    var calculate = function(operator) {
        fetch('/', {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify ({
                a: document.getElementsByName("a")[0].value,
                b: document.getElementsByName("b")[0].value,
                operator: operator
            }),
        }).then(
            function(response) {return response.json()
        }).then(
            function(data) {document.getElementById('result').innerText = data;
        }).catch(function() {});
    };
    document.getElementById('add').onclick = function(event) {calculate('+'); return false;};
    document.getElementById('subtract').onclick = function(event) {calculate('-'); return false;};
    document.getElementById('multiply').onclick = function(event) {calculate('*'); return false;};
    document.getElementById('divide').onclick = function(event) {calculate('/'); return false;};
});
