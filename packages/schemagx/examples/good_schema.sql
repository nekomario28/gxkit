-- A schema whose references all resolve.
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    total INTEGER NOT NULL
);
