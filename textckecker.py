from flask import Flask, request, render_template
import os

app = Flask(__name__)
#app.config.from_object(__name__ + '.ConfigClass')  # configuration

# Get the directory of the current script
current_directory = os.path.dirname(os.path.realpath(__file__))

# Home page
@app.route('/', methods=['GET'])
def home():
    # render home.html template
    return render_template("home.html")

@app.route('/submit', methods=['POST'])
def submit():
    user_text = request.form['user_text']
    return render_template("home.html", user_text=user_text)

if __name__ == '__main__':
    app.run(debug=True)
