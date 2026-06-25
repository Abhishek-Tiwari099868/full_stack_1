from selectors import SelectSelector
from flask import Flask, render_template, request, session,redirect,flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from datetime import datetime
import json
import os
from flask_mail import Mail
from sqlalchemy import or_


if os.path.exists("config.json"):
    with open("config.json", "r") as c:
        params = json.load(c)["params"]
else:
    params = {
        "secret_key": os.getenv("SECRET_KEY"),
        "gmail-user": os.getenv("MAIL_USERNAME"),
        "gmail-password": os.getenv("MAIL_PASSWORD"),
        "admin_username": os.getenv("ADMIN_USERNAME"),
        "admin_password": os.getenv("ADMIN_PASSWORD"),
        "local_url": os.getenv("DATABASE_URL"),
        "prod_url": os.getenv("DATABASE_URL"),
        "upload_location": "static/assets/img",

        "no_of_posts": 3,

        "tw_url": "#",
        "fb_url": "#",
        "gh_url": "#"
    }

local_server = os.path.exists("config.json")
app = Flask(__name__)
app.secret_key = params['secret_key']
app.config['UPLOAD_FOLDER'] = params['upload_location']
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME=params['gmail-user'],
    MAIL_PASSWORD=params['gmail-password']
)
mail = Mail(app)
if local_server:
      app.config["SQLALCHEMY_DATABASE_URI"] = params['local_url']
else:
      app.config["SQLALCHEMY_DATABASE_URI"] = params['prod_url']
db = SQLAlchemy(app)

class Contact(db.Model):
    __tablename__ = 'contacts'
    sr_no = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=False)
    date = db.Column(db.String(50), nullable=False)

class posts(db.Model):
    __tablename__ = 'posts'
    sr_no = db.Column(db.Integer, primary_key=True)
    Title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    tagline = db.Column(db.Text)
    date = db.Column(db.String(50))
    img_file = db.Column(db.String(255))
@app.route('/')
def index():
    all_posts = posts.query.all()[0:params['no_of_posts']]
    return render_template('index.html',params=params,posts=all_posts)

@app.route('/about')
def about():
    return render_template('about.html',params=params)

@app.route('/login',methods=['GET','POST'])
def login():
    all_posts = posts.query.all()
    if('user' in session and session['user']==params['admin_username']):
        return render_template('dashboard.html',params=params,posts=all_posts)

    if request.method == 'POST':
      username=request.form.get('username')
      userpass=request.form.get('password')
      if(username==params['admin_username'] and userpass==params['admin_password']):
    #Set the session varibale
        session['user']=username
        return render_template('dashboard.html',params=params,posts=all_posts)

    return render_template('login.html',params=params)

@app.route('/dashboard')
def dashboard():

    if 'user' not in session:
        return redirect('/login')

    all_posts = posts.query.all()

    return render_template(
        'dashboard.html',
        params=params,
        posts=all_posts
    )


@app.route('/post/')
def post():
    return render_template('post.html',params=params)

@app.route('/post/<string:post_slug>',methods=['GET'])
def post_route(post_slug):
    post = posts.query.filter_by(slug=post_slug).first()
    print("Slug:", post_slug)
    print("Post:", post)

    if post is None:
        return "Post Not Found"

    return render_template('db_post.html',params=params,post=post)


@app.route('/older-posts')
def older_posts():
    return render_template('older_posts.html', params=params)

@app.route('/edit/<string:sr_no>', methods=['GET', 'POST'])
def edit(sr_no):

    if 'user' not in session:
        return redirect('/login')

    if request.method == 'POST':

        print("POST HIT")
        print("SR_NO =", sr_no)
        print("Title =", request.form.get('Title'))

        if sr_no == '0':

            post = posts(
                Title=request.form.get('Title'),
                tagline=request.form.get('tagline'),
                slug=request.form.get('slug'),
                content=request.form.get('content'),
                img_file=request.form.get('img_file'),
                date=datetime.now().strftime("%Y-%m-%d")
            )

            print("TITLE =", post.Title)

            db.session.add(post)

        else:

            post = posts.query.filter_by(sr_no=sr_no).first()

            print("EDITING POST =", post)

            post.Title = request.form.get('Title')
            post.tagline = request.form.get('tagline')
            post.slug = request.form.get('slug')
            post.content = request.form.get('content')
            post.img_file = request.form.get('img_file')

        db.session.commit()

        print("COMMIT SUCCESS")

        return redirect('/dashboard')

    post = posts.query.filter_by(sr_no=sr_no).first()

    return render_template(
        'edit.html',
        params=params,
        post=post
    )

@app.route('/uploader', methods=['GET', 'POST'])
def upload_file():

    if 'user' not in session:
        return redirect('/login')

    if request.method == 'POST':

        f = request.files.get('img_file')

        if f and f.filename != '':
            filename = secure_filename(f.filename)

            f.save(
                os.path.join(
                    app.config['UPLOAD_FOLDER'],
                    filename
                )
            )

            return "Uploaded Successfully"

        return "No file selected"

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')


@app.route('/delete/<string:sr_no>')
def delete(sr_no):

    if 'user' not in session:
        return redirect('/login')

    post = posts.query.filter_by(sr_no=sr_no).first()

    if post:
        db.session.delete(post)
        db.session.commit()

    return redirect('/dashboard')

@app.route('/search')
def search():

    query = request.args.get('query', '').strip()

    if not query:
        return render_template(
            'search.html',
            params=params,
            posts=None
        )

    results = posts.query.filter(
        or_(
            posts.Title.ilike(f"%{query}%"),
            posts.tagline.ilike(f"%{query}%"),
            posts.content.ilike(f"%{query}%"),
            posts.slug.ilike(f"%{query}%")
        )
    ).order_by(posts.sr_no.desc()).all()

    return render_template(
        'search.html',
        params=params,
        posts=results,
        query=query
    )

@app.route('/contact', methods=['GET', 'POST'])
def contact():

    if request.method == 'POST':

        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')

        entry = Contact(
            Name=name,
            email=email,
            phone_number=phone,
            message=message,
            date=datetime.now().strftime("%Y-%m-%d")
        )

        db.session.add(entry)
        db.session.commit()
        db.session.add(entry)
db.session.commit()
try:
    mail.send_message(
        'New Message From ' + name,
        sender=params['gmail-user'],
        recipients=[params['gmail-user']],
        body=message + "\n" + phone
    )
except Exception as e:
    print(e)

flash("Thanks for contacting us!", "success")
return redirect("/contact")


if __name__ == '__main__':
    app.run()
