from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, ValidationError
from app.main.models import Todo

class TodoForm(FlaskForm):
    task = StringField('Task', validators = [DataRequired()])
    add = SubmitField('Add') 

    def validate_task(self, task):
        task = Todo.query.filter_by(task=task.data).first()
        if task and not task.is_completed:
            raise ValidationError('This Task already exist, complete That first ')
