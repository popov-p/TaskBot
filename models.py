from peewee import *

db = SqliteDatabase('tasks.db')

class Task(Model):
    id = AutoField()
    user_id = IntegerField(null=False)
    header = TextField(null=True, unique=True)
    description = TextField(null=True)
    date = DateField(null=True)
    time = TimeField(null=True)
    attachments = BooleanField(default=False)
    is_periodic = BooleanField(default=False)
    is_edited = BooleanField(default=False)
    interval = IntegerField(null=True)
    is_finished = BooleanField(default=False)
    user_notified = BooleanField(default=False)
    class Meta:
        database = db