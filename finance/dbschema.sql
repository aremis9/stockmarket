

CREATE TABLE users (
    id INTEGER,
    username TEXT NOT NULL,
    hash TEXT NOT NULL,
    cash NUMERIC NOT NULL DEFAULT 10000.00,
    PRIMARY KEY(id)
);

CREATE UNIQUE INDEX username ON users (username);



CREATE TABLE portfolio (
id INTEGER,
action TEXT,
symbol TEXT NOT NULL,
name TEXT,
shares INTEGER,
price REAL,
amount REAL,
date TEXT,
FOREIGN KEY (id) REFERENCES users(id)
);




CREATE TABLE stocks (
    id INTEGER,
    symbol TEXT NOT NULL,
    PRIMARY KEY(id)
);