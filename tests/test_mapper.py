from flask import Flask, redirect, render_template

app = Flask(__name__)


@app.route("/")
def test_mapper():
    query = "hi"
    return render_template("mapper.html", query=query)
