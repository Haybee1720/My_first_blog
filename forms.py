from datetime import date
from flask_gravatar import Gravatar
from flask_wtf import FlaskForm
from flask import Flask, render_template, request, url_for, redirect, flash, send_from_directory, abort
from wtforms import StringField, SubmitField, PasswordField, validators, EmailField
from wtforms.validators import DataRequired, URL
from flask_ckeditor import CKEditorField, CKEditor
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_bootstrap import Bootstrap
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import relationship


app = Flask(__name__)
app.config['SECRET_KEY'] = 'jaiejk#ae())3hw398hj/42$J@@$%^%$^%Wfjdjhu'
ckeditor = CKEditor(app)
Bootstrap(app)

app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///main"
app.config['SQLALCHEMY_BINDS'] = {
    'blog': 'sqlite:///blog.db',
    'user': 'sqlite:///user.db',
    'comments': 'sqlite:///comments.db'
}
app.config['SQLALCHEMY_SILENCE_UBER_WARNING'] = 1
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


##WTForm
class CreatePostForm(FlaskForm):
    author = StringField('Author Name', validators=[DataRequired()])
    title = StringField("Blog Post Title", validators=[DataRequired()])
    subtitle = StringField("Subtitle", validators=[DataRequired()])
    img_url = StringField("Blog Image URL", validators=[DataRequired(), URL()])
    body = CKEditorField("Blog Content", validators=[DataRequired()])
    submit = SubmitField("Submit Post")

class RegisterForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired()])
    password = PasswordField('Password', [validators.DataRequired()])
    name = StringField("Name", validators=[DataRequired()])
    submit = SubmitField("Submit")

class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired()])
    password = PasswordField('Password', [validators.DataRequired()])
    submit = SubmitField("Submit")

class CommentForm(FlaskForm):
    comment = CKEditorField('Comment')
    submit = SubmitField('SUBMIT COMMENT')

# #Table in DATAbase
class User(UserMixin, db.Model):
    __tablename__ = "users"
    __bind_key__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))

    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship('Comment', back_populates='comment_author')


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    __bind_key__ = 'blog'
    id = db.Column(db.Integer, primary_key=True)

    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey(User.id))
    # Create reference to the User object, the "posts" refers to the posts protperty in the User class.
    author = relationship("User", back_populates="posts")

    # Create reference to the Comment object.
    comments = relationship('Comment', back_populates='parent_post')

    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    img_url = db.Column(db.String(250))
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)


class  Comment(db.Model):
    __tablename__ = "comments"
    __bind_key__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    comment = db.Column(db.Text)
    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))

    # Create reference to the User object, the "posts" refers to the posts protperty in the User class.
    comment_author  = relationship("User", back_populates="comments")

    # Create Foreign Key, "BlogPost.id".
    post_id = db.Column(db.Integer, db.ForeignKey(BlogPost.id))
    # Create reference to the BlogPost object.
    parent_post = relationship("BlogPost", back_populates="comments")

with app.app_context():
    db.create_all()


@app.route('/')
def get_all_posts():
    all_posts = db.session.query(BlogPost).all()
    return render_template("index.html", all_posts=all_posts)


@app.route("/register", methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    error = None
    if form.validate_on_submit():
        #Check if user email already exist's in the database and if it does they get redirected to
        #lgin.html and get an error message else the data is added to the db
        user_email = User.query.filter_by(email=form.email.data).first()
        if user_email:
            error = "You already have an account, kindly login."
            login_form = LoginForm(email=form.email.data)
            return render_template("login.html", form=login_form, error=error)
        else:
            #Add user's data to the database
            new_data = User(
                email=form.email.data,
                password=generate_password_hash(password=form.password.data, method='pbkdf2:sha256', salt_length=10),
                name=form.name.data.title()
            )
            db.session.add(new_data)
            db.session.commit()
            login_user(new_data)
            return redirect(url_for("get_all_posts"))
    return render_template("register.html", form=form, error=error)


@app.route("/login", methods=['GET', 'POST'])
def login():
    # global user_details
    form = LoginForm()
    error = None
    if form.validate_on_submit():
        #Checks if email entered is in the database
        user_details = User.query.filter_by(email=form.email.data).first()
        if user_details == None:
            error = "Sorry, there's no account with that email."
            return render_template("login.html", form=form, error=error)
        else:
            check = check_password_hash(pwhash=user_details.password, password=form.password.data)
            if check:
                if user_details.id == 1:
                    admin = True
                login_user(user_details)
                return redirect(url_for("get_all_posts"))
            else:
                error = 'Your details is incorrect.'
    return render_template("login.html", form=form, error=error)


@app.route("/show_post/<int:post_id>", methods=['GET', 'POST'])
def show_post(post_id):
    comment_form = CommentForm()
    post = BlogPost.query.filter_by(id=post_id).first()

    all_comments = Comment.query.filter_by(post_id=post_id).all()


    gravatar = Gravatar(app,
                        size=100,
                        rating='g',
                        default='retro',
                        force_default=False,
                        force_lower=False,
                        use_ssl=False,
                        base_url=None)

    if comment_form.validate_on_submit():
        #if user is logged in
        if current_user.is_authenticated:
            new_comment = Comment(
                comment=comment_form.comment.data,
                post_id=post_id,
                user_id=current_user.id
            )
            db.session.add(new_comment)
            db.session.commit()
            return redirect(url_for('show_post', post_id=post_id))
        #Else user is not logged in
        else:
            form = LoginForm()
            error = 'You need to login to comment.'
            return render_template("login.html", form=form, error=error)
    return render_template('post.html', post=post, form=comment_form, all_comments=all_comments, gravatar=gravatar)


def admin_only(function):
    def wrapper_function():
        if current_user.id == 1:
            return function()
        else:
            abort(403)

    wrapper_function.__name__ = function.__name__
    return wrapper_function


@app.route("/add_new_post", methods=['POST', 'GET'])
@admin_only
def add_new_post():
    form = CreatePostForm(author=current_user.name)
    today = date.today()
    if form.validate_on_submit():
        new_post = BlogPost(author_id=current_user.id,
                            subtitle=form.subtitle.data.title(),
                            title=form.title.data,
                            img_url=form.img_url.data,
                            date=today.strftime("%B %d, %Y"),
                            body=form.body.data)
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, is_edit=False)


@app.route('/edit_post/<int:post_id>', methods=['POST', 'GET'])
def edit_post(post_id):
    post = BlogPost.query.filter_by(id=post_id).first()
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author.name,
        body=post.body
    )

    if edit_form.validate_on_submit():
        with app.app_context():
            post_to_update = BlogPost.query.get(int(post_id))
            post_to_update.title = edit_form.title.data
            post_to_update.subtitle = edit_form.subtitle.data
            post_to_update.img_url = edit_form.img_url.data
            post_to_update.author.name = edit_form.author.data
            post_to_update.body = edit_form.body.data
            db.session.commit()
        return redirect(url_for('show_post', post_id=post_id))
    return render_template("make-post.html", is_edit=True, form=edit_form)

@app.route('/delete_post')
@admin_only
def delete_post():
    return ("this is just a test")


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for("get_all_posts"))



@app.route("/about")
def about():
    pass


@app.route("/contact")
def contact():
    pass


if __name__ == "__main__":
    app.run(debug=True)