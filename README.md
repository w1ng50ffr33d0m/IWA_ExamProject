# Rinascita Tours - IWA Exam Project
![](./static/rinascita_tours_logo.png)
<p align="center">
   You can view the live demo <a target="_blank" href="https://dsdesi.eu.pythonanywhere.com">here</a>!
</p>

## Overview

A web platform for managing walking tours in the city of Rinascita! It allows guides to create and manage tours, and participants to browse and book available tours.

<p style="margin: 0.5rem 0; font-weight: bold">Technologies:</p>

<ul style="padding: 0 auto; margin: 0 auto;">
  <li>Front-end: Vanilla HTML/CSS, JS (little), Bootstrap</li>
  <li>Back-end: Flask, Flask-Login, SQLite</li>
</ul>

## Features

- Tour creation with mandatory information (5 photos, 4+ stops, non-overlapping schedules)
- Advanced tour filtering (date, duration, language)
- Reservation system with slots and 24-hour cancellation
- Post-tour reporting from guides, with evidence photos

## Getting Started

### Prerequisites
- Python 3.8+
- pip

### Installation

0. If using **virtual environments**, create one and source it:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

1. Install Dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run:
   ```bash
   python app.py
   ```
   The server will start `http://localhost:3000` by default.

## Account Types

Three types of users are supported:

1. **Guides**: Can create and manage tours, view reservations, submit post-tour reports
2. **Participants**: Can browse tours, make reservations, cancel bookings, and view their tour history
3. **Admins**: Can view platform statistics and guide/tour information

## Testing Credentials

### Guides

|  Name | Email | Password | Languages |
|-------|-------|----------|-----------|
| Carlotta Montelli | c.montelli@guide.com | OrangeEspresso | English, Italian, German |
| Tern Brant | t.brant@guide.com | PurityStrength | English, Spanish, Portuguese |

### Participants

|  Name | Email | Password |
|-------|-------|----------|
| Cantarella Fisalia | c.fisalia@participant.com | HomemadePanini |
| Ciaccona Toccata | c.toccata@participant.com | PastaBocadillo |
| Phoebe Marino | p.marino@participant.com | ASliceofPizza |

### Admins

|  Name | Email | Password |
|-------|-------|----------|
| Rover Solaris | rover@admin.com | TheUnwrittenOne |

## Testing Tips

### Scenario 1: Tour Creation & Reservation
1. Login as a guide
2. Create a new tour with:
   - Title, description, 5 photos
   - Weekly schedule (select 2-3 days)
   - 4+ stops, meeting point, duration, max participants
3. Logout, then login as a participant
4. Search and filter tours on homepage
5. Click a tour and make a reservation for an available date

### Scenario 2: Schedule Overlap
1. Login as a participant
2. Make a reservation for "Gryphon's Fortess" on any given Tuesday (later than today)
3. Go back and make a reservation for "Masterpieces of the Golden Age" on the same Tuesday
4. The application should reject the request due to overlap
5. This can be repeated with the same tour as well (e.g. booking from "Gryphon's Fortress" twice, on the same date)

### Scenario 3: Reservation Capacity
1. Login as a guide
2. Create a tour with max_participants = 2
3. Logout, then login as a participant
4. Book for two people
5. Login into a different participant account
6. Try to book one person
7. The application should reject the request due to max capacity

### Scenario 4: Cancellation Policy
1. Login as a participant
2. Make a reservation for a tour >24 hours away
3. "Cancel" button should be active, click and confirm cancellation
4. Make another reservation for a tour <24 hours away
5. "Cancel" button should be disabled

### Scenario 5: Tour Reporting (No Duplicates)
1. Login as a guide
2. Navigate to a completed tour date with reservations
3. Submit a report with a participant count and a sample evidence photo
4. Repeat steps 2 and 3 for the same tour date
5. The application should reject the request due to duplicate reports

### Scenario 6: Tour Modification Restrictions
1. Login as a guide
2. Create a tour
3. Try to modify any tour field (schedule, meeting point, etc.)
4. Logout, then login as a participant
5. Reserve a spot for the created tour
6. Logout, then login as the guide you initially created the tour with
7. Repeat step 3
8. The application should reject the request on non-editable fields, since someone has already booked the tour

### Scenario 7: Admin Dashboard
1. Login as Rover Solaris (admin) and navigate to the admin dashboard
2. View total guides, participants, tours, reservations
3. View reservations per language
4. Browse all guides and their tours

## Database Schema

### Users
```
users
+-----------------+-----------+---------------------------+
| Column Name     | Data Type | Constraints               |
+-----------------+-----------+---------------------------+
| id              | INTEGER   | PRIMARY KEY AUTOINCREMENT |
| first_name      | TEXT      | NOT NULL                  |
| last_name       | TEXT      | NOT NULL                  |
| email           | TEXT      | NOT NULL UNIQUE           |
| password        | TEXT      | NOT NULL                  |
| role            | TEXT      | NOT NULL                  |
| languages       | TEXT      |                           |
| description     | TEXT      |                           |
| profile_picture | TEXT      |                           |
+-----------------+-----------+---------------------------+
```

### Tours
```
tours
+------------------+-----------+---------------------------+
| Column Name      | Data Type | Constraints               |
+------------------+-----------+---------------------------+
| id               | INTEGER   | PRIMARY KEY AUTOINCREMENT |
| guide_id         | INTEGER   | NOT NULL, FK(users.id)    |
| title            | TEXT      | NOT NULL                  |
| meeting_point    | TEXT      | NOT NULL                  |
| duration         | INTEGER   | NOT NULL                  |
| language         | TEXT      | NOT NULL                  |
| max_participants | INTEGER   | NOT NULL                  |
| description      | TEXT      | NOT NULL                  |
+------------------+-----------+--------------------------+

tour_schedules
+-------------+-----------+---------------------------+
| Column Name | Data Type | Constraints               |
+-------------+-----------+---------------------------+
| id          | INTEGER   | PRIMARY KEY AUTOINCREMENT |
| tour_id     | INTEGER   | NOT NULL, FK(tours.id)    |
| weekday     | TEXT      | NOT NULL                  |
| start_time  | TEXT      | NOT NULL                  |
+-------------+-----------+---------------------------+

tour_stops
+-------------+-----------+---------------------------+
| Column Name | Data Type | Constraints               |
+-------------+-----------+---------------------------+
| id          | INTEGER   | PRIMARY KEY AUTOINCREMENT |
| tour_id     | INTEGER   | NOT NULL, FK(tours.id)    |
| stop_name   | TEXT      | NOT NULL                  |
| stop_order  | INTEGER   |                           |
+-------------+-----------+---------------------------+

tour_photos
+-------------+-----------+---------------------------+
| Column Name | Data Type | Constraints               |
+-------------+-----------+---------------------------+
| id          | INTEGER   | PRIMARY KEY AUTOINCREMENT |
| tour_id     | INTEGER   | NOT NULL, FK(tours.id)    |
| tour_photos | TEXT      | NOT NULL                  |
+-------------+-----------+---------------------------+
```

### Reservations
```
reservations
+----------------+-----------+---------------------------+
| Column Name    | Data Type | Constraints               |
+----------------+-----------+---------------------------+
| id             | INTEGER   | PRIMARY KEY AUTOINCREMENT |
| participant_id | INTEGER   | NOT NULL, FK(users.id)    |
| tour_id        | INTEGER   | NOT NULL, FK(tours.id)    |
| tour_date      | TEXT      | NOT NULL                  |
| num_people     | INTEGER   | NOT NULL                  |
| extra_names    | TEXT      |                           |
+----------------+-----------+---------------------------+
```

### Reports
```
reports
+---------------------+-----------+---------------------------+
| Column Name         | Data Type | Constraints               |
+---------------------+-----------+---------------------------+
| id                  | INTEGER   | PRIMARY KEY AUTOINCREMENT |
| tour_id             | INTEGER   | NOT NULL, FK(tours.id)    |
| tour_date           | TEXT      | NOT NULL                  |
| actual_participants | INTEGER   | NOT NULL                  |
| evidence_photos     | TEXT      | NOT NULL                  |
+---------------------+-----------+---------------------------+
```
