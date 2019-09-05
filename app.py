#!/usr/bin/python3

from flask import Flask
#from flask import render_template

from colletor_manager import CollectorManager
import json
from bson import json_util
from bson.json_util import dumps

app = Flask(__name__)
manager = CollectorManager()
manager.start_manager()

# @app.route("/perfchecker")
# def index():
#     return render_template("index.html")

@app.route("/perfchecker")
def perfchecker_results():
    results = manager.get_metrics_from_server()
    json_results = json.dumps(results, default=json_util.default)
    return json_results

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8081, debug=True, use_reloader=False)