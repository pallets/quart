# Todo App
This is a minimal todo list app to showcase application factory using quart

To run this app export create_app() as quart_app and run quart 
```Bash
$ export QUART_APP="app:create_app()"
$ quart run
```

To re-create database delete `Database/database.db` and run **quart shell** 
```Python
$ quart shell
>>>from app.extinsions import db
>>>db.create_all(app=app)
```
