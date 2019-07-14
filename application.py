import os
import requests

from flask import Flask, flash, jsonify, redirect, render_template, request, session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from flask_session import Session

from helpers import login_required, apology

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Display searched book(s)"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Query database for books
        rows = db.execute("SELECT * FROM books WHERE title LIKE :search OR author LIKE :search OR year LIKE :search OR isbn LIKE :search ORDER BY year DESC",
                          {"search": "%"+(request.form.get("search"))+"%"}).fetchall()

        if len(rows) < 1:
            flash('Book not found!')
            return redirect("/")

        # Storing books data in a list
        books = []
        for row in rows:
            data = {"book_id": row["book_id"], "ISBN": row["isbn"], "Title": row["title"], "Author": row["author"], "Year": row["year"]}
            books.append(data)

        # Rendering search.html disaplying every book
        return render_template("search.html", books=books)

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("search.html")

@app.route("/book/<int:book_id>")
@login_required
def book(book_id):
    """Display selected book and display reviews"""

    # Make sure book exists.
    row = db.execute("SELECT * FROM books WHERE book_id = :book_id", {"book_id": book_id}).fetchone()
    if row is None:
        return apology("No such book", 404)

    # Get book data
    book_data = {"book_id": row["book_id"], "ISBN": row["isbn"], "Title": row["title"], "Author": row["author"], "Year": row["year"]}

    # Get all reviews
    rows = db.execute("SELECT user_id, rating, review, date FROM reviews WHERE book_id = :book_id ORDER BY review_id DESC", {"book_id": book_id}).fetchall()
    reviews = []
    for review in rows:
        # Date in English format
        date = review["date"].strftime("%b %d, %Y")
        # Get username
        username = db.execute("SELECT username FROM users WHERE user_id = :user_id", {"user_id": review["user_id"]}).fetchone()
        # Create dictionary of row data and append it to list
        data = {"user_id": review["user_id"], "rating": review["rating"], "review": review["review"], "date": date, "username": username[0]}
        reviews.append(data)

    # Data from Goodreads
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "7y3GhV8Mp5JJQOL9FuwQfQ", "isbns": row["isbn"]}).json()
    book_data["average_rating"] = res['books'][0]['average_rating']
    book_data["number_of_ratings"] = res['books'][0]['work_ratings_count']

    # Rendering book.html disaplying selected book
    return render_template("book.html", book=book_data, reviews=reviews)


@app.route("/api/<isbn>")
def api(isbn):
    """Display book data in json format"""

    # Make sure book exists.
    row = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
    print(row)
    if row is None:
        return apology("No such book", 404)

    # Data from Goodreads and store in book's dictionary
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "7y3GhV8Mp5JJQOL9FuwQfQ", "isbns": row["isbn"]}).json()

    # Rendering book.html disaplying selected book
    return jsonify(title=row["title"],
                   author=row["author"],
                   year=int(row["year"]),
                   isbn=row["isbn"],
                   reviews_count=int(res['books'][0]['reviews_count']),
                   average_score=float(res['books'][0]['average_rating']))


@app.route("/add_review", methods=["POST"])
@login_required
def add_review():
    """Add review"""

    # Ensure review added
    if not request.form.get("review"):
        return apology("must add a review", 400)

    # Ensure book already not reviewed
    reviwed = db.execute("SELECT * FROM reviews WHERE user_id = :user_id AND book_id = :book_id",
                         {"user_id": session["user_id"], "book_id": request.form.get("book_id")}).fetchone()
    if reviwed:
        return apology("Already Reviewed", 403)

    # Add review to db
    db.execute("INSERT INTO reviews (user_id, book_id, rating, review) VALUES (:user_id, :book_id, :rating, :review)",
               {"user_id": session["user_id"],
                "book_id": request.form.get("book_id"),
                "rating": request.form.get("rating"),
                "review": request.form.get("review")})
    db.commit()

    # Rendering book.html disaplying selected book
    flash("Review added!")
    return redirect("/book/" + request.form.get("book_id"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          {"username": request.form.get("username")}).fetchall()

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["password"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["user_id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure username's length > 3
        elif not len(request.form.get("username")) > 3:
            return apology("username must be at least 4 characters long", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Ensure password's length > 7
        elif not len(request.form.get("password")) > 7:
            return apology("password must be at least 8 characters long", 400)

        # Ensure password was confirmed correctly
        elif not request.form.get("password") == request.form.get("confirmation"):
            return apology("password must match", 400)

        # Hash the password
        hashed = generate_password_hash(request.form.get("password"))

        # Ensure username is not already taken
        new_user = db.execute("SELECT username FROM users WHERE username = :username", {"username": request.form.get("username")}).fetchone()
        if new_user:
            return apology("username already exists", 400)

        # Register user in database
        db.execute("INSERT INTO users (username, password) VALUES(:username, :password)",
                   {"username": request.form.get("username"), "password": hashed})
        db.commit()
        # Get user_id of newly created user
        rows = db.execute("SELECT user_id FROM users WHERE username=:username",
                          {"username": request.form.get("username")}).fetchall()

        # Remember the logged in user
        session["user_id"] = rows[0]["user_id"]

        # Redirect user to home page
        flash('Account created successfully! You were successfully logged in!')
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
