from flask import Flask
from logging import getLogger
from threading import Thread
getLogger('werkzeug').disabled = True
app = Flask('')
@app.get('/')
def root():
    return 'Hello, website is live at root'

def runner():
    app.run(host = '0.0.0.0', port=8080)
def ka():
    t = Thread(target=runner)
    t.start()