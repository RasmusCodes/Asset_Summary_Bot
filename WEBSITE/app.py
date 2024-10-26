import os

import sqlite3
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

from datetime import datetime

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
connection = sqlite3.connect("database.db", check_same_thread=False)
connection.row_factory = sqlite3.Row  # To access columns by name
db = connection.cursor()


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    cash = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])[0]["cash"]
    total = cash

    stocks = db.execute("SELECT * FROM portfolio WHERE user_id = ?", session["user_id"])
    for holding in stocks:
        holding["value"] = holding["amount"] * lookup(holding["ticker"])["price"]
        holding["price"] = lookup(holding["ticker"])["price"]
        total += holding["value"]
    return render_template("index.html", stocks=stocks, cash=usd(cash), total=usd(total))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        try:
            shares = int(request.form.get("shares"))
        except:
            return apology("Invalid shares")
        if shares < 1:
            return apology("Invalid shares")
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("Missing symbol")
        data = lookup(symbol)
        if not data:
            return apology("Invalid symbol")

        user = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
        money = user[0]["cash"]
        if money < data["price"] * shares:
            return apology("Can't afford")

        date = datetime.now()
        db.execute("UPDATE users SET cash = ? WHERE id = ?", money - data["price"] * shares, session["user_id"])
        connection.commit()

        curr_shares = db.execute(
            "SELECT * FROM portfolio WHERE user_id = ? AND ticker = ?", session["user_id"], symbol.upper())
        if len(curr_shares) == 0:
            db.execute("INSERT INTO portfolio (user_id, ticker, amount, date) VALUES (?, ?, ?, ?)",
                       session["user_id"], symbol.upper(), shares, date.strftime("%d/%m/%Y %H:%M:%S"))
        else:
            new_shares = curr_shares[0]["amount"] + shares
            db.execute("UPDATE portfolio SET amount = ?, date = ? WHERE user_id = ? AND ticker = ?",
                       new_shares,  date.strftime("%d/%m/%Y %H:%M:%S"), session["user_id"], symbol.upper())

        db.execute("INSERT INTO transactions (user_id, ticker, shares, price, type, date) VALUES (?, ?, ?, ?, ?, ?)",
                   session["user_id"], symbol.upper(), shares, data["price"], "buy", date.strftime("%d/%m/%Y %H:%M:%S"))

        return redirect("/")
    else:
        return render_template("buy.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        username = request.form.get("username")
        password = request.form.get("password")
        if not username:
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not password:
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchall()

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

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
    if request.method == "POST":
        name = request.form.get("username")
        if not name:
            return apology("Missing username")

        users = db.execute("SELECT username FROM users WHERE username = ?", name)
        if users:
            return apology("Username taken")

        pw = request.form.get("password")
        if not pw:
            return apology("Missing password")
        pwcheck = request.form.get("confirmation")
        if pw != pwcheck:
            return apology("Passwords don't match")

        """Register user"""
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)",
                   name, generate_password_hash(pw))
        session["user_id"] = db.execute("SELECT id FROM users WHERE username = ?", name)[0]["id"]
        return redirect("/")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "POST":
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("Missing symbol")
        try:
            sell_shares = int(request.form.get("shares"))
            if sell_shares < 1:
                return apology("Shares must be positive")
        except:
            return apology("Invalid input")

        stock = db.execute("SELECT * FROM portfolio WHERE user_id = ? AND ticker = ?",
                           session["user_id"], symbol.upper())
        if len(stock) == 0:
            return apology("Symbol not owned")

        current_shares = stock[0]["amount"]
        if sell_shares > current_shares:
            return apology("Too many shares")

        data = lookup(symbol)
        sell_value = sell_shares * data["price"]

        user = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
        balance = user[0]["cash"] + sell_value
        db.execute("UPDATE users SET cash = ? WHERE id = ?", balance, session["user_id"])
        connection.commit()
        if sell_shares == current_shares:
            db.execute("DELETE FROM portfolio WHERE user_id = ? and ticker = ?",
                       session["user_id"], symbol.upper())
        else:
            db.execute("UPDATE portfolio SET amount = ? WHERE user_id = ? AND ticker = ?",
                       current_shares - sell_shares, session["user_id"], symbol.upper())

        date = datetime.now()
        db.execute("INSERT INTO transactions (user_id, ticker, shares, price, type, date) VALUES (?, ?, ?, ?, ?, ?)",
                   session["user_id"], symbol.upper(), - sell_shares, data["price"], "sell", date.strftime("%d/%m/%Y %H:%M:%S"))

        return redirect("/")

    else:
        tickers = db.execute("SELECT ticker FROM portfolio WHERE user_id = ?", session["user_id"])
        tickers = [row["ticker"] for row in tickers]
        return render_template("sell.html", tickers=tickers)


@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():
    user = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    money = user[0]["cash"]
    if request.method == "POST":
        try:
            depo = int(request.form.get("deposit"))
            if money + depo < 0:
                return apology("Insufficient funds")
        except:
            return apology("Invalid input")
        db.execute("UPDATE users SET cash = ? WHERE id = ?", money + depo, session["user_id"])
        connection.commit()
        return redirect("/")
    else:
        return render_template("deposit.html", balance=usd(money))

@app.teardown_appcontext
def close_connection(exception):
    if connection:
        connection.close()