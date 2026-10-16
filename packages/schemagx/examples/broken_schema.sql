-- A schema with a dangling reference and a key type that does not match its target.
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    owner_id INTEGER NOT NULL REFERENCES owners(id)
);
