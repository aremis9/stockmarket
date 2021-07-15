# Get all stock symbols from IEX and insert into database
# For asynchronoud searching

import os
import requests
import urllib.parse
from cs50 import SQL
from flask import jsonify

db = SQL("sqlite:///finance.db")


def getstocks():
    # Contact API
    try:
        api_key = os.environ.get("API_KEY")
        url = f"https://cloud.iexapis.com/beta/ref-data/symbols?token={api_key}"
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        quote = response.json()
        stocks = []
        count = 0
        for stock in quote:
            # db.execute("INSERT INTO stocks (symbol) VALUES (?)", stock["symbol"])
            count += 1
        return count  # count must be 10930
    except (KeyError, TypeError, ValueError):
        return None

# count = getstocks()
# print(count)

# # search = request.args.get('q')
# search = "AA"
# query = db.execute(f'SELECT symbol FROM stocks WHERE symbol LIKE("%{str(search)}%")')
# # query = db_session.query(Movie.title).filter(Movie.title.like('%' + str(search) + '%'))
# results = [symbol["symbol"] for symbol in query]
# print(jsonify(results))


search = "AA"
query = db.execute("SELECT symbol FROM stocks WHERE symbol LIKE ?", "%" + search + "%")
# query = db_session.query(Movie.title).filter(Movie.title.like('%' + str(search) + '%'))
results = [symbol["symbol"] for symbol in query]
print(results)