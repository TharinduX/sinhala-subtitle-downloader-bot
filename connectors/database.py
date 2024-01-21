import sqlite3


def connect_db():
    return sqlite3.connect('connectors/movie_details.db')


def create_table_movie():
    conn = connect_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS movie_details
    (movie_id text UNIQUE, movie_name text, year text, baiscope_link text, overview text)''')
    conn.commit()
    conn.close()


def create_table_tv():
    conn = connect_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tv_details (series_id text, series_name text, year text, season integer, 
    episode integer, baiscope_link text UNIQUE, overview text, updated text)''')
    conn.commit()
    conn.close()


def insert_details(movie_id, movie_name, year, baiscope_link, overview):
    conn = connect_db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO movie_details VALUES (?,?,?,?,?)",
              (movie_id, movie_name, year, baiscope_link, overview))
    conn.commit()
    conn.close()


def get_link(movie_id):
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT baiscope_link FROM movie_details WHERE movie_id = ?", (movie_id,))
    result = c.fetchone()
    if result is None:
        conn.close()
        return None
    else:
        link = result[0]
        conn.close()
        return link


def insert_tv_details(series_id, series_name, year, season, episode, baiscope_link, overview, updated):
    conn = connect_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO tv_details VALUES (?,?,?,?,?,?,?,?)",
              (series_id, series_name, year, season, episode, baiscope_link, overview, updated))
    conn.commit()
    conn.close()


def get_series_links(series_id, season):
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT episode, baiscope_link, updated, series_name FROM tv_details WHERE series_id = ? AND season = ?",
              (series_id, season))
    rows = c.fetchall()
    if rows is None:
        conn.close()
        return None
    else:
        return sorted([(season, row[0], row[1], row[2], row[3]) for row in rows], key=lambda x: x[1])


def get_series_name(series_id):
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT series_name FROM tv_details WHERE series_id = ? ", (series_id,))
    result = c.fetchone()
    if result is None:
        conn.close()
        return None
    else:
        series_name = result[0]
        conn.close()
        return series_name


def check_series_available(series_id):
    conn = connect_db()
    c = conn.cursor()
    # Execute a SELECT statement to check if the series_id exists
    c.execute("SELECT series_name, year, season, episode, baiscope_link, overview, updated FROM tv_details WHERE "
              "series_id = ?",
              (series_id,))
    result = c.fetchall()
    conn.close()
    return result


def fetch_old_data(series_id):
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT series_name, year, season, episode, baiscope_link, overview, updated FROM tv_details WHERE "
              "series_id = ?",
              (series_id,))
    result = c.fetchall()
    conn.close()
    return result


def search_tv_series(series_name):
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT series_id FROM tv_details WHERE series_name = ?", (series_name,))
    result = c.fetchone()
    if result is None:
        conn.close()
        return None
    else:
        series_id = result[0]
        conn.close()
        return series_id
