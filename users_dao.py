import sqlite3
from constants import DB

def get_user_by_id(user_id):
    # fetches a user by their id
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    sql = 'SELECT * FROM users WHERE id = ?'
    cursor.execute(sql, (user_id,))
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    return user

def get_user_by_email(email):
    # fetches a user by their email
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    sql = 'SELECT * FROM users WHERE email = ?'
    cursor.execute(sql, (email,))
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    return user

def add_user(user_data):
    # insert new user in database
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    success = False

    sql = 'INSERT INTO users(first_name, last_name, email, password, role, languages) VALUES (?, ?, ?, ?, ?, ?)'

    try:
        cursor.execute(sql, (
            user_data['first_name'],
            user_data['last_name'], 
            user_data['email'],
            user_data['password'],
            user_data['role'],
            user_data.get('languages', None)
        ))
        conn.commit()
        success = True
    except Exception as e:
        print('Error adding user:', str(e))
        conn.rollback()
    
    cursor.close()
    conn.close()

    return success

def get_all_guides():
    # returns a list of all guides for admin page
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    sql = 'SELECT * FROM users WHERE role = ?'
    cursor.execute(sql, ('guide',))
    guides = cursor.fetchall()

    cursor.close()
    conn.close()

    return guides

def get_admin_stats():
    # returns statistics for the admin dashboard
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    stats = {}

    sql_guides = 'SELECT COUNT(*) FROM users WHERE role = "guide"'
    cursor.execute(sql_guides)
    stats['tot_guides'] = cursor.fetchone()[0]

    sql_participants = 'SELECT COUNT(*) FROM users WHERE role = "participant"'
    cursor.execute(sql_participants)
    stats['tot_participants'] = cursor.fetchone()[0]

    sql_tours = 'SELECT COUNT(*) FROM tours'
    cursor.execute(sql_tours)
    stats['tot_tours'] = cursor.fetchone()[0]

    sql_reservations = 'SELECT COUNT(*) FROM reservations'
    cursor.execute(sql_reservations)
    stats['tot_reservations'] = cursor.fetchone()[0]

    sql_res_per_lang = '''
        SELECT tours.language, COUNT(reservations.id)
        FROM reservations
        JOIN tours ON reservations.tour_id = tours.id
        GROUP BY tours.language
    '''
    cursor.execute(sql_res_per_lang)
    
    results = cursor.fetchall()
    stats['res_per_language'] = {}
    for row in results:
        language = row[0]
        count = row[1]
        stats['res_per_language'][language] = count

    cursor.close()
    conn.close()

    return stats

def update_user_profile(user_id, description, profile_picture):
    # update guide public profile information
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    success = False

    sql = 'UPDATE users SET description = ?, profile_picture = ? WHERE id = ?'

    try:
        cursor.execute(sql, (description, profile_picture, user_id))
        conn.commit()
        success = True
    except Exception as e:
        print('Error updating profile:', str(e))
        conn.rollback()

    cursor.close()
    conn.close()

    return success
