from flask import abort, request, Flask

app = Flask(__name__)


@app.route("/", methods=("GET", "POST"))
def index():
    if request.method == "GET":
        abort(501)
    elif request.method == "POST":
        abort(501)
