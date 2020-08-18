from app.extinsions import db

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task = db.Column(db.String(20), nullable=False)
    is_completed = db.Column(db.Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"List[task: '{self.task}', Completed: '{self.is_completed}']"

