import os
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from TextAnalysis import TextAnalysis
from ImageAnalysis import ImageAnalysis
import pymongo
import uuid
from functools import wraps
import json
from passlib.hash import pbkdf2_sha256

app = Flask(__name__)

# database
client = pymongo.MongoClient('localhost', 27017)
db = client.mydatabase

app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

# Decorators

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            return redirect('/')
    return wrap

def start_session(user):
    # del user['password']
    session['logged_in'] = True
    session['user'] = user
    return jsonify(user), 200

@app.route('/')
def homepage(logged_in=None):
    try:
        logged_in = session['logged_in']
        return render_template('homepage.html', logged_in)
    except:
        return render_template('homepage.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        # print(request.form)
        # Create the user object
        user = {
            "_id": uuid.uuid4().hex,
            "name": request.form.get('name'),
            "email": request.form.get('email'),
            "password": request.form.get('password')
        }
        
        user['password'] = pbkdf2_sha256.encrypt(user['password'])
        
        # Check for existing email address
        if db.users.find_one({"email": user['email']}):
            # return jsonify({"error": "Email address already in use"}), 400

            return render_template("register.html", error= "Email address already in use")

        if db.users.insert_one(user):
            # return start_session(user)
            return redirect(url_for('login'))

    return render_template("register.html")

@app.route('/signout')
def signout():
    session.clear()
    return redirect('/')



@app.route('/login', methods=['GET', 'POST'])
def login(error = None):

    if request.method == 'POST':
        user = db.users.find_one({
            "email": request.form.get('email')
        })

        if user:
            user_password = user['password']
            # if request.form.get('password') ==  user_password:
            
            if pbkdf2_sha256.verify(request.form.get('password'), user_password):
                user_name = user['name']
                start_session(user_name)
                return redirect(url_for('dashboard'))
            else:
                error = "Invalid credentials"
                return render_template('login.html', error = error)
        else:
            error = "Invalid credentials"
            return render_template('login.html', error = error)
    return render_template('login.html', error = error)


@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard(logged_in = None):
    logged_in = session['logged_in']
    # user_name = session['user']
    # `print`(user_name)
    text_analysis_activated = True
    return render_template('dashboard.html', text_analysis_activated = text_analysis_activated, logged_in=logged_in)

@app.route('/analyzing', methods=['GET', 'POST'])
@login_required
def analyzing(logged_in = None):
    if request.method == 'POST':
        logged_in = session['logged_in']
        text_analysis = TextAnalysis(request.form['text'])
        text_analysis_activated = True
        return render_template('dashboard.html', dictionary_response=text_analysis.get_response(), text_analysis_activated = text_analysis_activated, logged_in=logged_in)
    else:
        return render_template('dashboard.html', dictionary_response=dict(),logged_in=logged_in)

app.config['IMAGE_UPLOADS'] = '.\\static\\gallery\\uploads'
app.config['IMAGE_DOWNLOADS'] = '.\\static\\gallery\\downloads'
# app.config['IMAGE_UPLOADS'] = 'C:\\Users\\Saksham\\p\\Python\\MLyze\\static\\gallery\\uploads'

@app.route('/image_analysis', methods=['GET', 'POST'])
@login_required
def image_analysis(logged_in = None):
    if request.method == 'POST':
        logged_in = session['logged_in']
        image = request.files['person_image']
        filename = image.filename
        image.save(os.path.join(app.config["IMAGE_UPLOADS"], filename))

        perform_image_analysis = ImageAnalysis(request.form['person_name'], filename)
        image_analysis_activated = True

        for file in os.listdir(app.config['IMAGE_DOWNLOADS']):
            os.remove(os.path.join(app.config['IMAGE_DOWNLOADS'], file))
        print()
        return render_template('dashboard.html', image_analysis_dictionary_response=perform_image_analysis.analyse(), image_analysis_activated = image_analysis_activated, logged_in=logged_in, filename=filename)
    else:
        image_analysis_activated = True
        return render_template('dashboard.html', dicttionary_response=dict(), image_analysis_activated=image_analysis_activated ,logged_in=logged_in)

@app.route('/text_analysis/<text>')
def test(text):
    text_analysis = TextAnalysis(text)
    dictionary_response = {'sentences': dict(), 'nouns': dict()}

    for key, value in text_analysis.get_response().items():
        if key == 'sentences':
            for sentence, polarity in text_analysis.get_response()[key].items():
                dictionary_response['sentences']['sentence'] = sentence
                dictionary_response['sentences']['polarity'] = polarity
        else:
            id = 0

            for noun in value:
                dictionary_response['nouns'][id] = noun
                id += 1

    return json.dumps(dictionary_response)

if __name__ == '__main__':
    app.run(debug=True)
