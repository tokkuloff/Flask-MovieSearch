import json
import threading


from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from flask_login import login_required, current_user, login_user, logout_user, UserMixin
from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import requests
from flask import Flask, render_template, url_for, redirect, request, session
from flask_sqlalchemy import SQLAlchemy

from flask_login import LoginManager
from wtforms import StringField, IntegerField, SubmitField
from wtforms.validators import DataRequired

app = Flask(__name__)
app.app_context().push()
app.secret_key = "123"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///imdb.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

db = SQLAlchemy(app)
db.init_app(app)
Bootstrap(app)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def repr(self):
        return f'<Users {self.id}>'


class Movie(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    title = db.Column(db.String(), unique=True)
    year = db.Column(db.String())
    released = db.Column(db.String())
    runtime = db.Column(db.String())
    genre = db.Column(db.String())
    director = db.Column(db.String())
    plot = db.Column(db.String())
    poster = db.Column(db.String())
    imdb = db.Column(db.String())
    imdbR = db.Column(db.String())
    country = db.Column(db.String())
    awards = db.Column(db.String())


class MovieForm(FlaskForm):
    title = StringField('title', validators=[DataRequired()])
    year = StringField('year', validators=[DataRequired()])
    released = StringField('released', validators=[DataRequired()])
    runtime = StringField('runtime', validators=[DataRequired()])
    genre = StringField('genre', validators=[DataRequired()])
    director = StringField('director', validators=[DataRequired()])
    plot = StringField('plot', validators=[DataRequired()])
    poster = StringField('poster', validators=[DataRequired()])
    imdb = StringField('imdb', validators=[DataRequired()])
    imdbR = StringField('imdbR', validators=[DataRequired()])
    country = StringField('country', validators=[DataRequired()])
    awards = StringField('awards', validators=[DataRequired()])
    submit = SubmitField('Submit')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
@app.route('/home')
def home_page():
    return render_template('home.html')


def save_changes(film: Movie, form: MovieForm, new=False):
    film.title = form.data['title']
    film.year = form.data['year']
    film.released = form.data['released']
    film.runtime = form.data['runtime']
    film.genre = form.data['genre']
    film.director = form.data['director']
    film.plot = form.data['plot']
    film.poster = form.data['poster']
    film.imdb = form.data['imdb']
    film.imdbR = form.data['imdbR']
    film.country = form.data['country']
    film.awards = form.data['awards']

    if new:
        # Add the new album to the database
        db.session.add(film)
    # commit the data to the database
    db.session.commit()


@app.route('/new_album', methods=['GET', 'POST'])
def new():
    form = MovieForm(request.form)
    if request.method == "POST" and form.validate():
        film = Movie()
        save_changes(film, form, new=True)
        return redirect(url_for("show_all_films"))
    return render_template('new.html', form=form)


@app.route('/film/<int:film_id>', methods=['GET'])
def get_film(film_id):
    m = Movie.query.filter_by(id=film_id).first()
    return render_template('result.html', m=m)



@app.route('/result', methods=['GET', 'POST'])
def result():
    a = request.values['url1']
    m = Movie.query.filter_by(title=a).first()
    if m:
        print('from db')
        return render_template('result.html', m=m)
    elif not m:
        url = "https://moviesdb5.p.rapidapi.com/om"
        querystring = {"t": a}
        headers = {
            "X-RapidAPI-Key": "5ec2c51d77mshc634c9c87ce90d1p1c8951jsnd15245ee0bb8",
            "X-RapidAPI-Host": "moviesdb5.p.rapidapi.com"
        }
        session1 = Session()
        session1.headers.update(headers)
        response = session1.get(url, params=querystring)
        if response.status_code == 200:
            print('from API')
            data = json.loads(response.text)
            title = data['Title']
            year = data['Year']
            released = data['Released']
            runtime = data['Runtime']
            genre = data['Genre']
            genres = ', '.join(genre)
            director = data['Director']
            directors = ', '.join(director)
            plot = data['Plot']
            poster = data['Poster']
            imdb = data['Ratings'][0]['Source']
            imdbR = data['Ratings'][0]['Value']
            country = data['Country']
            awards = data['Awards']

            m1 = Movie(title=title.lower(),
                       year=year,
                       released=released,
                       runtime=runtime,
                       genre=genre,
                       director=director,
                       plot=plot,
                       poster=poster,
                       imdb=imdb,
                       imdbR=imdbR,
                       country=country,
                       awards=awards)

            db.session.add(m1)
            db.session.commit()

            return render_template('result.html', headers=headers, params=querystring, m=m1)
        else:
            return render_template('error.html')

    else:
        return render_template('error.html')


@app.route('/log', methods=['GET', 'POST'])
def login():
    mesage = ''
    if request.method == "POST":
        user = db.session.query(User).filter_by(email=request.form['email'],
                                                password=request.form['password']).first()
        if user:
            login_user(user)
            mesage = 'Logged in successfully !'
            return redirect(url_for("home_page", id=user.id))
        else:
            mesage = 'Please enter correct email / password !'
    return render_template('log.html', mesage=mesage)


@app.route('/reg', methods=['GET', 'POST'])
def register():
    mesage = ''
    if request.method == "POST":
        name = request.form['username']
        email = request.form['email']
        password = request.form['password']
        data = db.session.query(User).filter_by(email=request.form['email']).first()
        if data:
            return redirect(url_for('error'))
        else:
            add_user(User(name=name,
                          email=email,
                          password=password))
            mesage = "You succesfully registered!"
        return render_template('log.html', mesage='Succesfully registered!')

    return render_template('reg.html', mesage=mesage)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home_page'))


@app.route('/error', methods=["GET"])
def error():
    return render_template('reg.html', mesage='User already exists')


ROWS_PER_PAGE = 5


@app.route('/films')
@login_required
def show_all_films():
    page = request.args.get('page', 1, type=int)

    films = Movie.query.paginate(page=page, per_page=ROWS_PER_PAGE)
    return render_template('films.html', films=films)


@app.route('/delete/<int:film_id>')
@login_required
def delete_film(film_id):
    film = Movie.query.filter_by(id=film_id).first()
    db.session.delete(film)
    db.session.commit()
    return redirect(url_for('show_all_films'))


@app.route('/edit/<int:film_id>', methods=['GET', 'POST'])
@login_required
def edit(film_id):
    film = db.session.query(Movie).filter_by(id=film_id).first()
    if film:
        form = MovieForm(formdata=request.form, obj=film)
        if request.method == 'POST' and form.validate():
            # save edits
            save_changes(film, form)
            return redirect(url_for('show_all_films'))
        return render_template('edit.html', form=form)
    else:
        return 'Error loading #{id}'.format(id=id)


def add_user(user: User) -> None:
    db.session.add(user)
    db.session.commit()


def delete_user(user: User) -> None:
    db.session.delete(user)
    db.session.commit()




def run_app():
    app.run(debug=False, threaded=True)


def custom():
    user = User(name='Islam', email='admin@movies.ru', password='123', is_admin=True)
    db.session.add(user)
    db.session.commit()


if __name__ == '__main__':
    db.create_all()

    first_thread = threading.Thread(target=run_app)
    second_thread = threading.Thread(target=custom)
    first_thread.start()
    second_thread.start()
