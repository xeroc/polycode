from . import app, tasks

assert app
assert tasks


@app.task()
def hello():
    return "hello world"


app.autodiscover_tasks()  # discovers tasks.py in all INSTALLED_APPS
