import os
# using cs50 helper module for sql
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd
import re
import datetime
import statistics

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


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


class User:
    def __init__(self, userid, name, cash):
        self.userid = userid
        self.name = name
        self.cash = cash
        self.action = ""
        self.ssymbol = ""
        self.sname = ""
        self.sprice = 0.0
        self.sshares = 0
        self.samount = 0.0
        self.sdate = ""
        self.newbal = 0.0


user = User(0, "Init", 0)

danger = "[^a-zA-Z0-9]"


def cashrefresh(user):
    user.cash = db.execute("SELECT cash FROM users WHERE username = ?", user.name)[0]["cash"]


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    global danger
    if request.method == "POST":

        # Ensure username AND password was submitted
        if not request.form.get("username") and not request.form.get("password"):
            return apology("Must provide username and password", 400)

        # Ensure username was submitted
        elif not request.form.get("username"):
            return apology("Must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("Must provide password", 400)

        # x = re.findall(danger, request.form.get("username"))
        # if len(x) != 0:
        #     return apology("Username must not contain any special characters", 400)

        # Check if username already exists
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        if len(rows) != 0:
            return apology("Username already exists", 400)
        # elif len(request.form.get("password")) < 8:
        #     return apology("Password must be atleast 8 characters", 400)
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("Passwords don't match", 400)
        else:
            db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", request.form.get("username"),
                       generate_password_hash(request.form.get("password")))
            return render_template("login.html")
    else:
        return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username AND password was submitted
        if not request.form.get("username") and not request.form.get("password"):
            return apology("Must provide username and password", 400)

        # Ensure username was submitted
        elif not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # x = re.findall(danger, request.form.get("username"))
        # if len(x) != 0:
        #     return apology("Username must not contain any special characters", 400)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 400)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        user.userid = rows[0]["id"]
        user.name = rows[0]["username"]
        user.cash = rows[0]["cash"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Show portfolio of stocks"""
    if request.method == "POST":
        global symbol
        if request.form.get("sellthis"):
            if request.form.get("sellthis") not in symbol:
                return apology("You don't own this stock!", 400)
            return render_template("sell.html", this=request.form.get("sellthis"), symbol=symbol, validsell=False, user=user)
        elif request.form.get("buythis"):
            return render_template("buy.html", this=request.form.get("buythis"), validbuy=False, user=user)
    else:
        # Hold is a dictionary with keys of: symbol, name, shares, price, amount
        # Hold identifies what stocks does the user holds.
        hold = [s for s in db.execute("SELECT DISTINCT symbol FROM portfolio WHERE id = ?", user.userid)]
        symbol = [s["symbol"] for s in hold]
        totalamount = user.cash

        for i in range(len(symbol)):
            query = db.execute("SELECT COUNT(symbol), name, SUM(shares) FROM portfolio WHERE symbol = ? AND id = ?",
                               symbol[i], user.userid)[0]
            price = [p["price"]
                     for p in db.execute("SELECT price FROM portfolio WHERE symbol = ? AND id = ?", symbol[i], user.userid)]
            amount = [a["amount"]
                      for a in db.execute("SELECT amount FROM portfolio WHERE symbol = ? AND id = ?", symbol[i], user.userid)]
            end = query["COUNT(symbol)"]
            try:
                hold[i]["name"] = query["name"]
                hold[i]["shares"] = query["SUM(shares)"]
                hold[i]["price"] = lookup(symbol[i])["price"]
                hold[i]["amount"] = sum(amount)
                totalamount += hold[i]["amount"]
            except:
                return apology("INVALID", 400)
            if hold[i]["shares"] == 0:
                hold.pop(i)

        hold.sort(key=lambda a: a["amount"], reverse=False)
        cashrefresh(user)
        return render_template("index.html", hold=hold, user=user, total=totalamount)


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("Must provide symbol", 400)
        stockinfo = lookup(request.form.get("symbol"))
        if stockinfo == None:
            return apology("Invalid symbol", 400)

        sname = stockinfo["name"]
        sprice = stockinfo["price"]
        ssymbol = stockinfo["symbol"]
        return render_template("quote.html", sname=sname, sprice=sprice, ssymbol=ssymbol, user=user)
    else:
        return render_template("quote.html", user=user)


validbuy = False


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    global validbuy

    if request.method == "POST":
        if validbuy == False:
            if not request.form.get("symbol") and not request.form.get("shares"):
                return apology("Must provide symbol and shares", 400)
            elif not request.form.get("symbol"):
                return apology("Must provide symbol", 400)
            elif not request.form.get("shares"):
                return apology("Must provide shares", 400)

            stock = lookup(request.form.get("symbol"))
            if stock == None:
                return apology("Invalid symbol", 400)

            x = re.findall("[^0-9]", request.form.get("shares"))
            if len(x) != 0:
                return apology("Shares must be a whole number", 400)

            try:
                user.sshares = int(request.form.get("shares"))
            except:
                return apology("Shares must be a whole number", 400)

            cashrefresh(user)
            user.action = "Buy"
            user.ssymbol = stock["symbol"]
            user.sname = stock["name"]
            user.sprice = stock["price"]
            user.sshares = int(request.form.get("shares"))
            user.samount = user.sprice * user.sshares
            user.newbal = user.cash - user.samount
            if user.samount > user.cash:
                return apology("Insufficient Balance", 400)

            validbuy = True
            return render_template("buy.html", validbuy=True, user=user)

        elif validbuy == True:
            validbuy = False
            db.execute("UPDATE users SET cash = ? WHERE username = ?", user.newbal, user.name)
            cashrefresh(user)
            user.sdate = datetime.datetime.now().replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
            db.execute("INSERT INTO portfolio VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       user.userid, user.action, user.ssymbol, user.sname,
                       user.sshares, user.sprice, user.samount, user.sdate)
            return redirect("/")

    else:
        validbuy = False
        cashrefresh(user)
        return render_template("buy.html", validbuy=False, user=user)


symbol = []
validsell = False


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    global validsell

    hold = [s for s in db.execute("SELECT DISTINCT symbol FROM portfolio WHERE id = ?", user.userid)]
    global symbol
    symbol = [s["symbol"] for s in hold]

    for i in range(len(symbol)):
        query = db.execute("SELECT COUNT(symbol), name, SUM(shares) FROM portfolio WHERE symbol = ? AND id = ?",
                           symbol[i], user.userid)[0]
        price = [p["price"]
                 for p in db.execute("SELECT price FROM portfolio WHERE symbol = ? AND id = ?", symbol[i], user.userid)]
        amount = [a["amount"]
                  for a in db.execute("SELECT amount FROM portfolio WHERE symbol = ? AND id = ?", symbol[i], user.userid)]
        end = query["COUNT(symbol)"]
        hold[i]["name"] = query["name"]
        hold[i]["shares"] = query["SUM(shares)"]
        hold[i]["price"] = lookup(symbol[i])["price"]
        hold[i]["amount"] = sum(amount)
        if hold[i]["shares"] == 0:
            symbol.pop(i)
            hold.pop(i)

    if request.method == "POST":
        if validsell == False:
            if not request.form.get("symbol") and not request.form.get("shares"):
                return apology("Must provide symbol and shares", 400)
            elif not request.form.get("symbol"):
                return apology("Must provide symbol", 400)
            elif not request.form.get("shares"):
                return apology("Must provide shares", 400)

            try:
                user.sshares = int(request.form.get("shares"))
            except:
                return apology("Shares must be a whole number", 400)

            selling = {
                "symbol": None,
                "shares": None
            }

            for h in hold:
                if h["symbol"] == request.form.get("symbol"):
                    selling["symbol"] = h["symbol"]
                    selling["shares"] = h["shares"]

            if selling["symbol"] == None or selling["shares"] == None:
                return apology("Invalid symbol and/or shares", 400)
            elif selling["shares"] < int(request.form.get("shares")) or selling["shares"] < 0:
                return apology("You do not own that much shares", 400)

            stock = lookup(request.form.get("symbol"))
            if stock == None:
                return apology("Invalid symbol", 400)

            cashrefresh(user)
            user.action = "Sell"
            user.ssymbol = request.form.get("symbol")
            user.sname = stock["name"]
            user.sprice = stock["price"]
            user.sshares = -int(request.form.get("shares"))
            user.samount = user.sprice * -user.sshares
            user.newbal = user.cash + user.samount

            validsell = True
            return render_template("sell.html", validsell=True, user=user)

        elif validsell == True:
            validsell = False
            db.execute("UPDATE users SET cash = ? WHERE username = ?", user.newbal, user.name)
            cashrefresh(user)
            user.sdate = datetime.datetime.now().replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
            db.execute("INSERT INTO portfolio VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       user.userid, user.action, user.ssymbol, user.sname,
                       user.sshares, user.sprice, -user.samount, user.sdate)
            return redirect("/")

    else:
        validsell = False
        cashrefresh(user)
        return render_template("sell.html", validsell=False, symbol=symbol, user=user)


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    transactions = db.execute("SELECT * FROM portfolio WHERE id = ?", user.userid)
    for trs in transactions:
        trs["amount"] = float(str(trs["amount"]).replace("-", ""))
    cashrefresh(user)
    return render_template("history.html", transactions=transactions, user=user)


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Asynchronous searching
@app.route('/search', methods=['GET'])
@login_required
def search():
    search = request.args.get('q')
    query = db.execute("SELECT symbol FROM stocks WHERE symbol LIKE ?", search + "%")
    results = [symbol["symbol"] for symbol in query]
    return jsonify(matching_results=results)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
