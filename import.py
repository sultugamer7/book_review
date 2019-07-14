import os
import csv

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

# Open books.csv file
f = open("books.csv")

# Get data from books.csv file
reader = csv.reader(f)

# Skip first row
next(reader)

# Importing the data in database
for isbn, title, author, year in reader:
    # Insert query
    db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
               {"isbn": isbn, "title": title, "author": author, "year": year})
    print(f"Added:\n    ISBN: {isbn}\n    Title: {title}\n    Author: {author}\n    Year: {year}")

# Transactions are assumed, so close the transaction finished
db.commit()

# Close opened file
f.close()
