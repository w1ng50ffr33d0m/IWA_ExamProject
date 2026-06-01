import sqlite3
from constants import DB
from datetime import datetime, timedelta

def get_tours(date_start=None, date_end=None, duration=None, languages=None):
    # returns list of tours based on selected filters (dhandles single dates or ranges)
    # convert calendar date into a weekday, assuming date has format YYYY-MM-DD
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    sql = '''
        SELECT tours.*, MIN(tour_photos.tour_photos) AS tour_image
        FROM tours
        LEFT JOIN tour_photos ON tours.id = tour_photos.tour_id
    '''
    params = []
    conditions = []

    if date_start or date_end:
        valid_weekdays = set()

        # if only one date is picked, use it for both bounds
        d_start = date_start if date_start else date_end
        d_end = date_end if date_end else date_start

        if d_start and d_end:
            try:
                start_dt = datetime.strptime(d_start, '%Y-%m-%d')
                end_dt = datetime.strptime(d_end, '%Y-%m-%d')

                # ensure start is always before end
                if start_dt > end_dt:
                    start_dt, end_dt = end_dt, start_dt

                # if range is 6 days or more, it covers every day of the week
                if (end_dt - start_dt).days >= 6:
                    valid_weekdays.update(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'])
                # else, calculate the weekdays covered
                else:
                    current_date = start_dt
                    while current_date <= end_dt:
                        weekday = current_date.strftime('%A')
                        valid_weekdays.add(weekday)
                        current_date += timedelta(days=1)

                if len(valid_weekdays) > 0:
                    placeholders = ','.join('?' * len(valid_weekdays))
                    sql += ' JOIN tour_schedules ON tours.id = tour_schedules.tour_id'
                    conditions.append(f'tour_schedules.weekday IN ({placeholders})')
                    params.extend(valid_weekdays)
            except ValueError:
                print('Invalid date format provided.')

    if duration:
        conditions.append('tours.duration <= ?')
        params.append(duration)

    if languages:
        placeholders = ','.join('?' * len(languages))
        conditions.append(f'tours.language IN ({placeholders})')
        params.extend(languages)

    if conditions:
        sql += ' WHERE ' + ' AND '.join(conditions)

    sql += ' GROUP BY tours.id' 

    cursor.execute(sql, params)
    tours = cursor.fetchall()

    cursor.close()
    conn.close()

    return tours

def get_tour_details(tour_id):
    # returns tour details for single tour page
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    sql = 'SELECT * FROM tours WHERE id = ?'
    cursor.execute(sql, (tour_id,))
    tour = cursor.fetchone()

    if not tour:
        cursor.close()
        conn.close()
        return None
    
    tour_details = dict(tour)

    # get stops
    sql_stops = 'SELECT * FROM tour_stops WHERE tour_id = ? ORDER BY stop_order'
    cursor.execute(sql_stops, (tour_id,))
    
    tour_details['stops'] = []
    for row in cursor.fetchall():
        tour_details['stops'].append(dict(row))

    # get schedules
    sql_schedules = 'SELECT * FROM tour_schedules WHERE tour_id = ?'
    cursor.execute(sql_schedules, (tour_id,))
    
    tour_details['schedules'] = []
    for row in cursor.fetchall():
        tour_details['schedules'].append(dict(row))

    # get photos
    sql_photos = 'SELECT * FROM tour_photos WHERE tour_id = ?'
    cursor.execute(sql_photos, (tour_id,))
    
    tour_details['photos'] = []
    for row in cursor.fetchall():
        tour_details['photos'].append(dict(row))
 
    cursor.close()
    conn.close()

    return tour_details

def get_tours_by_guide(guide_id):
    # returns list of tours given the guide
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    sql = '''
        SELECT tours.*, MIN(tour_photos.tour_photos) AS tour_image
        FROM tours 
        LEFT JOIN tour_photos ON tours.id = tour_photos.tour_id
        WHERE tours.guide_id = ? 
        GROUP BY tours.id
    '''
    cursor.execute(sql, (guide_id,))
    tours = cursor.fetchall()

    cursor.close()
    conn.close()

    return tours

def create_tour(tour_data):
    # inserts new tour and relative data in the database
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    success = False

    sql_tour = 'INSERT INTO tours (guide_id, title, meeting_point, duration, language, max_participants, description) VALUES (?, ?, ?, ?, ?, ?, ?)'
    sql_photo = 'INSERT INTO tour_photos (tour_id, tour_photos) VALUES (?, ?)'
    sql_stop = 'INSERT INTO tour_stops (tour_id, stop_name, stop_order) VALUES (?, ?, ?)'
    sql_schedule = 'INSERT INTO tour_schedules (tour_id, weekday, start_time) VALUES (?, ?, ?)'

    try:
        # insert data into tours table
        cursor.execute(sql_tour, (
            tour_data['guide_id'],
            tour_data['title'],
            tour_data['meeting_point'],
            tour_data['duration'],
            tour_data['language'],
            tour_data['max_participants'],
            tour_data['description']
        ))
        
        # takes id of tour just created
        new_tour_id = cursor.lastrowid
        
        # insert photos -> tour_data["photos"] has to be a list of 5 paths
        if 'photos' in tour_data:
            for path in tour_data['photos']:
                cursor.execute(sql_photo, (new_tour_id, path))
                
        # insert stops -> tour_data['stops'] has to be a list of stop names
        if 'stops' in tour_data:
            for order, stop_name in enumerate(tour_data['stops'], start=1):
                cursor.execute(sql_stop, (new_tour_id, stop_name, order))

        # insert schedules -> tour_data["schedules"] has to be a list of dicts {"weekday": "monday", "start_time": "11:00"}
        if "schedules" in tour_data:
            for schedule in tour_data["schedules"]:
                cursor.execute(sql_schedule, (new_tour_id, schedule["weekday"], schedule["start_time"]))
        
        conn.commit()
        success = True
    except Exception as e:
        print('Error creating tour:', str(e))
        conn.rollback()

    cursor.close()
    conn.close()

    return success

def update_tour(tour_id, updated_data):
    # updates tour data and its related tables in the database
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    success = False

    sql_main = '''
        UPDATE tours 
        SET title = ?, meeting_point = ?, duration = ?, language = ?, max_participants = ?, description = ? 
        WHERE id = ?
    '''
    
    try:
        # update main tour table
        cursor.execute(sql_main, (
            updated_data['title'],
            updated_data['meeting_point'],
            updated_data['duration'],
            updated_data['language'],
            updated_data['max_participants'],
            updated_data['description'],
            tour_id
        ))

        # update stops
        if "stops" in updated_data:
            cursor.execute("DELETE FROM tour_stops WHERE tour_id = ?", (tour_id,))
            sql_stop = "INSERT INTO tour_stops (tour_id, stop_name, stop_order) VALUES (?, ?, ?)"
            for order, stop_name in enumerate(updated_data["stops"], start=1):
                cursor.execute(sql_stop, (tour_id, stop_name, order))

        # update schedules
        if "schedules" in updated_data:
            cursor.execute("DELETE FROM tour_schedules WHERE tour_id = ?", (tour_id,))
            sql_schedule = "INSERT INTO tour_schedules (tour_id, weekday, start_time) VALUES (?, ?, ?)"
            for schedule in updated_data["schedules"]:
                cursor.execute(sql_schedule, (tour_id, schedule["weekday"], schedule["start_time"]))

        # if the user didn't upload new photos, we reuse the old paths
        if "photos" in updated_data and updated_data["photos"]:
            cursor.execute("DELETE FROM tour_photos WHERE tour_id = ?", (tour_id,))
            sql_photo = "INSERT INTO tour_photos (tour_id, tour_photos) VALUES (?, ?)"
            for path in updated_data["photos"]:
                cursor.execute(sql_photo, (tour_id, path))

        conn.commit()
        success = True
    except Exception as e:
        print('Error updating tour:', str(e))
        conn.rollback()

    cursor.close()
    conn.close()

    return success

def get_all_guide_schedules(guide_id, exclude_tour_id=None):
    # gets all weekly schedules for a specific guide to check for overlaps
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    sql = '''
        SELECT ts.weekday, ts.start_time, t.duration, t.title
        FROM tour_schedules ts
        JOIN tours t ON ts.tour_id = t.id WHERE t.guide_id = ?
    '''
    params = [guide_id]

    # avoid tour conflicting with itself
    if exclude_tour_id:
        sql += ' AND t.id != ?'
        params.append(exclude_tour_id)

    cursor.execute(sql, params)
    schedules = cursor.fetchall()
    
    formatted_schedules = []
    for sched in schedules:
        formatted_schedules.append(dict(sched))
        
    cursor.close()
    conn.close()

    return formatted_schedules

def add_tour_report(report_data):
    # add tour report in the database
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    success = False

    sql = '''
        INSERT INTO reports (tour_id, tour_date, actual_participants, evidence_photos) 
        VALUES (?, ?, ?, ?)
    '''
    
    try:
        cursor.execute(sql, (
            report_data['tour_id'],
            report_data['tour_date'],
            report_data['actual_participants'],
            report_data['evidence_photos'],
        ))
        conn.commit()
        success = True
    except Exception as e:
        print('Error creating report:', str(e))
        conn.rollback()
        
    cursor.close()
    conn.close()

    return success

def check_report_exists(tour_id, tour_date):
    # checks if a report was already submitted for a specific date
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    sql = 'SELECT id FROM reports WHERE tour_id = ? AND tour_date = ? LIMIT 1'
    cursor.execute(sql, (tour_id, tour_date))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    if result is not None:
        return True
    else:
        return False