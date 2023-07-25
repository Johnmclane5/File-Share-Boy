from flask import Flask, render_template
from threading import Thread
import os

app = Flask(__name__)

@app.route('/')
def index():
    return "🗄File-Share-Boy👦"

def run():
    # Check if the PORT environment variable exists
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

if __name__ == "__main__":
    # In case you want to run the app directly using python script.py
    keep_alive()
