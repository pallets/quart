from app.extinsions import db
from app.main import main
from quart import render_template, redirect, url_for
from app.main.models import Todo
from app.main.forms import TodoForm

@main.route('/')
async def home():
  form = TodoForm()
  todos = Todo.query.filter_by(is_completed=False).order_by(Todo.id.desc()).all()
  return await render_template('index.html', todos=todos, form = form)

@main.route('/add', methods = ['POST'])
async def add():
  form = TodoForm()
  if form.validate_on_submit():
    task = Todo(task = form.task.data)
    db.session.add(task)
    db.session.commit()
  return redirect(url_for('main.home'))

@main.route('/trash/<int:id>')
async def trash(id):
  task = Todo.query.get(int(id))
  db.session.delete(task)
  db.session.commit()
  return redirect(url_for('main.home'))

@main.route('/check/<int:id>')
async def check(id):
  task = Todo.query.get(int(id))
  task.is_completed = True
  db.session.commit()
  return redirect(url_for('main.home'))
