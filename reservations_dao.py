import sqlite3
from constants import DB

def add_reservation(reservation_data):
    # insert a new reservation
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    success = False

    sql = "INSERT INTO reservations (participant_id, tour_id, tour_date, num_people, extra_names) VALUES (?, ?, ?, ?, ?)"

    try:
        cursor.execute(sql, (
            reservation_data["participant_id"],
            reservation_data["tour_id"],
            reservation_data["tour_date"],
            reservation_data["num_people"],
            reservation_data.get("extra_names", "")
        ))
        conn.commit()
        success = True
    except Exception as e:
        print('Error creating reservation:', str(e))
        conn.rollback()

    cursor.close()
    conn.close()

    return success

def get_reservation_by_id(reservation_id):
    # get reservation by its id
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    sql = 'SELECT * FROM reservations WHERE id = ?'
    cursor.execute(sql, (reservation_id,))
    reservation = cursor.fetchone()

    cursor.close()
    conn.close()

    if reservation:
        return dict(reservation)
    
    return None

def get_reserv_by_participant(participant_id):
    # return reservations + tour details so the participant knows where to go
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # JOIN with tours to get title, meeting point and duration for the dashboard
    sql = '''
        SELECT reservations.*, tours.title, tours.meeting_point, tours.duration
        FROM reservations
        JOIN tours ON reservations.tour_id = tours.id
        WHERE reservations.participant_id = ?
    '''
    
    cursor.execute(sql, (participant_id,))
    reservations = cursor.fetchall()

    cursor.close()
    conn.close()

    return reservations

def get_reservations_by_tour(tour_id):
    # return reservations + participant details so the guide knows who is coming
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # JOIN with users to get the actual names and emails of the participants
    sql = '''
        SELECT reservations.*, users.first_name, users.last_name, users.email
        FROM reservations
        JOIN users ON reservations.participant_id = users.id
        WHERE reservations.tour_id = ?
    '''
    cursor.execute(sql, (tour_id,))
    reservations = cursor.fetchall()

    cursor.close()
    conn.close()

    return reservations

def delete_reservation(reservation_id):
    # cancel a reservation
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    success = False

    sql = 'DELETE FROM reservations WHERE id = ?'

    try:
        cursor.execute(sql, (reservation_id,))
        conn.commit()
        success = True
    except Exception as e:
        print('Error deleting reservation:', str(e))
        conn.rollback()
    
    cursor.close()
    conn.close()

    return success

def get_bookings_for_date(tour_id, date):
    # count all people currently booked for a specific date
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    # add up the num_people column
    sql = 'SELECT SUM(num_people) FROM reservations WHERE tour_id = ? AND tour_date = ?'
    cursor.execute(sql, (tour_id, date))
    
    result = cursor.fetchone()[0] # if no rows match, returns a tuple like (10,) or (None,)

    cursor.close()
    conn.close()

    if result is not None:
        return result
    else:
        return 0

def check_if_reservations(tour_id):
    # check if a tour has any upcoming reservations to lock edit button
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    from datetime import datetime
    today_str = datetime.now().strftime('%Y-%m-%d')

    sql = 'SELECT id FROM reservations WHERE tour_id = ? AND tour_date >= ? LIMIT 1'
    cursor.execute(sql, (tour_id, today_str))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    if result is not None:
        return True
    else:
        return False

def get_participant_bookings_for_date(participant_id, date):
    # get all bookings a participant has on a specific date to check for overlaps
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    sql = 'SELECT * FROM reservations WHERE participant_id = ? AND tour_date = ?'
    cursor.execute(sql, (participant_id, date))
    bookings = cursor.fetchall()

    cursor.close()
    conn.close()

    formatted_bookings = []
    for b in bookings:
        formatted_bookings.append(dict(b))

    return formatted_bookings

def get_participant_tour_bookings(participant_id, tour_id):
    # get specific dates a participant has booked for a single tour
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    sql = 'SELECT tour_date FROM reservations WHERE participant_id = ? AND tour_id = ? ORDER BY tour_date ASC'
    cursor.execute(sql, (participant_id, tour_id))
    bookings = cursor.fetchall()

    cursor.close()
    conn.close()

    formatted_dates = []
    for b in bookings:
        formatted_dates.append(dict(b))

    return formatted_dates