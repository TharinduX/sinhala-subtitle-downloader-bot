import sqlite3

def connect_db():
    return sqlite3.connect('movie_details.db')

def create_table():
    conn = connect_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS movie_details
    (movie_id text UNIQUE, movie_name text, year text, baiscope_link text, overview text)''')
    conn.commit()
    conn.close()

def insert_details(movie_id, movie_name, year, baiscope_link, overview):
    conn = connect_db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO movie_details VALUES (?,?,?,?,?)", (movie_id, movie_name, year, baiscope_link, overview))
    conn.commit()
    conn.close()

def get_link(movie_id):
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT baiscope_link FROM movie_details WHERE movie_id = ?", (movie_id,))
    link = c.fetchone()[0]
    conn.close()
    return link
