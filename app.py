# IMPORT MODULE
import os
from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import date, datetime, timedelta
from flask_login import (
    LoginManager,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash
import users_dao, tours_dao, reservations_dao, utility
from models import User
from PIL import Image

# CREATE APPLICATION
app = Flask(__name__)

app.config["SECRET_KEY"] = "Sp4cetrekC0llective"

login_manager = LoginManager()
login_manager.init_app(app)

# SIGNUP PAGE
@app.route("/signup")
def signup():
    return render_template("signup.html")

# signup logic
@app.route("/signup", methods=["POST"])
def signup_post():
    new_user_form = request.form.to_dict()

    # check that all required fields have been filled
    utility.check_general_fields(
        ["first_name", "last_name", "email", "password"], 
        new_user_form,
        url_for("signup")
    )

    # guide signup logic and check that they put at least one language during sign up
    if new_user_form.get("role") == "guide":
        languages_list = request.form.getlist("languages")
        if not languages_list:
            flash("Guides must select at least one language.", "danger")
            return redirect(url_for("signup"))
        new_user_form["languages"] = ", ".join(languages_list)
    else:
        new_user_form["languages"] = ""

    # load user by email inserted in the email field
    user_in_db = users_dao.get_user_by_email(new_user_form.get("email"))

    # check that email is unique among all users
    if user_in_db:
        flash("Email is already in use.", "danger")
        return redirect(url_for("signup"))
    else:
        new_user_form["password"] = generate_password_hash(
            new_user_form.get("password")
        )
        
        success = users_dao.add_user(new_user_form)

        if success:
            flash("Registration complete.", "success")
            
            # retrieve newly created user
            new_user_db = users_dao.get_user_by_email(new_user_form.get("email"))
            
            # log user in directly after sign up and show the home page
            new_user = User(
                id = new_user_db["id"],
                first_name = new_user_db["first_name"],
                last_name = new_user_db["last_name"],
                email = new_user_db["email"],
                password = new_user_db["password"],
                role = new_user_db["role"],
                languages = new_user_db["languages"],
                description = new_user_db["description"],
                profile_picture = new_user_db["profile_picture"]
            )
            login_user(new_user, True)
            
            return redirect(url_for("home"))
        else:
            flash("Error: user creation failed, try again.", "danger")

    return redirect(url_for("signup"))

# LOGIN
@app.route("/login", methods=["POST"])
def login():
    user_form = request.form.to_dict()

    user_db = users_dao.get_user_by_email(user_form["email"])

    # save previous page url (so when login modal closes user remains on the page that triggered the modal) and go back to home page if url is missing
    next_page = request.referrer or url_for("home")

    # check that credentials match the database ones
    if not user_db or not check_password_hash(
        user_db["password"], user_form["password"]
    ):
        flash("Wrong credentials, retry", "danger")
        return redirect(next_page)
    else:
        # log user in
        new_user = User.load_from_database(user_db)
        login_user(new_user, True)
        flash(f"Welcome back, {new_user.first_name}!", "success")

        return redirect(next_page)

# load user data after login
@login_manager.user_loader
def load_user(user_id):
    user_db = users_dao.get_user_by_id(user_id)
    if user_db is not None:
        user = User.load_from_database(user_db)
    else:
        user = None

    return user

# logout logic
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))


# HOME PAGE
@app.route("/")
def home():
    date_start = request.args.get("date_start")
    date_end = request.args.get("date_end")
    duration_filter = request.args.get("duration")
    lang_filter = request.args.getlist("lang")

    # get tours based on the given filters; if filters are empty, get all tours
    tours_db = tours_dao.get_tours(date_start, date_end, duration_filter, lang_filter)
        
    # set is faster for lookups
    booked_tour_ids = set() 
    
    # participant home page logic (showing "booked" badges)
    if current_user.is_authenticated and current_user.role == "participant":
        user_reservations = reservations_dao.get_reserv_by_participant(current_user.id)
        
        for res in user_reservations:
            # check if reservation is in the future
            tour_date = res["tour_date"]
            tour_id = res["tour_id"]
            
            # find the scheduled weekday for the tour
            tour_info = tours_dao.get_tour_details(tour_id)

            try:
                weekday = utility.get_weekday(tour_date, app.logger,  "Invalid weekday found for the reservation.")
            except ValueError:
                continue
            
            # find start time for that weekday
            start_time = "00:00"
            for sched in tour_info["schedules"]:
                if sched["weekday"] == weekday:
                    start_time = sched["start_time"]
                    break
            
            # combine to full datetime
            res_datetime = datetime.strptime(f"{tour_date} {start_time}", "%Y-%m-%d %H:%M")
            
            # only add to the list if it is in the future
            if res_datetime > datetime.now():
                booked_tour_ids.add(tour_id)
            
    return render_template("home.html", tours=tours_db, booked_tour_ids=booked_tour_ids)


# SINGLE TOUR PAGE
@app.route("/tours/<int:id>")
def single_tour(id):
    tour_db = tours_dao.get_tour_details(id)
    
    user_bookings = []
    if current_user.is_authenticated and current_user.role == "participant":
        # get participant reservations for a specific tour
        bookings = reservations_dao.get_participant_tour_bookings(current_user.id, id)
        
        # prepare the list for the template
        for booking in bookings:
            booking_dict = dict(booking)
            # create a date object for comparison
            booking_dict["tour_date_obj"] = datetime.strptime(booking_dict["tour_date"], "%Y-%m-%d").date()
            user_bookings.append(booking_dict)
        
    return render_template(
        "tour_details.html", 
        tour = tour_db, 
        user_bookings = user_bookings,
        today = datetime.now().date()
    )


# PARTICIPANT PAGE
@app.route("/participant_page")
@login_required
def participant_page():
    # check current user is a participant
    if current_user.role != "participant":
        flash("Access restricted to participants.", "danger")
        return redirect(url_for("home"))
    
    # get all reservations for the participant
    reservations_db = reservations_dao.get_reserv_by_participant(current_user.id)
    
    # initialize separate lists for past and upcoming reservations
    past_reservations = []
    upcoming_reservations = []
    
    for reservation in reservations_db:
        reservation_dict = dict(reservation)
        
        # calculate if tour is more than 24 hours away
        tour_date_str = reservation_dict["tour_date"]
        try:
            weekday = utility.get_weekday(tour_date_str, app.logger,  "Invalid weekday found for the reservation.")
        except ValueError:
            continue
            
        tour = tours_dao.get_tour_details(reservation_dict["tour_id"])
        start_time_str = "00:00"
        # find matching weekday and update start time
        for schedule in tour["schedules"]:
            if schedule["weekday"] == weekday:
                start_time_str = schedule["start_time"]
                break
                
        reservation_dict["start_time"] = start_time_str
        full_start_time_str = f"{tour_date_str} {start_time_str}"
        tour_datetime = datetime.strptime(full_start_time_str, "%Y-%m-%d %H:%M")
        
        # sort into past or upcoming reservations
        now = datetime.now()
        if tour_datetime < now:
            reservation_dict["can_cancel"] = False
            past_reservations.append(reservation_dict)
        else:
            if tour_datetime - now >= timedelta(hours=24):
                reservation_dict["can_cancel"] = True
            else:
                reservation_dict["can_cancel"] = False
            upcoming_reservations.append(reservation_dict)

    # pass both lists to the template
    return render_template(
        "participant_page.html", 
        upcoming_reservations = upcoming_reservations, 
        past_reservations = past_reservations
    )

# GUIDE PAGE (PRIVATE)
@app.route("/guide_page")
@login_required
def guide_page():
    # check current user is a guide
    if current_user.role != "guide":
        flash("Access restricted to guides.", "danger")
        return redirect(url_for("home"))
    
    # fetch all tours for the guide
    tours_db = tours_dao.get_tours_by_guide(current_user.id)
    tours_with_reservations = []
    
    for tour in tours_db:
        tour_dict = dict(tour)
        # get tour schedule details
        tour_details = tours_dao.get_tour_details(tour["id"])
        schedules = tour_details["schedules"]

        # get all reservations for each tour
        reservations = reservations_dao.get_reservations_by_tour(tour["id"])
        
        # group reservations by date
        grouped_reservations = {}
        for res in reservations:
            res_dict = dict(res)
            tour_date_str = res_dict["tour_date"]
            
            # if reservation not in group, initialize its structure
            if tour_date_str not in grouped_reservations:
                try:
                    # get weekday
                    weekday = utility.get_weekday(tour_date_str, app.logger,  "Invalid weekday found for the reservation.")
                    # find start time for weekday
                    start_time = "00:00"
                    for sched in schedules:
                        if sched["weekday"] == weekday:
                            start_time = sched["start_time"]
                            break
                except ValueError:
                    # if date format is wrong, use a placeholder
                    start_time = "To Be Determined"
                    
                # structure of data for each reservation
                grouped_reservations[tour_date_str] = {
                    "start_time": start_time,
                    "total_expected": 0,
                    "details": []
                }
            
            # update reservation data with total people that reserved
            grouped_reservations[tour_date_str]["total_expected"] += res_dict["num_people"]
            grouped_reservations[tour_date_str]["details"].append(res_dict)

        # Split into past and current reservations
        today_str = date.today().isoformat()
        current_reservations = {}
        past_reservations = {}
        for reservation_date, data in sorted(grouped_reservations.items()):
            if reservation_date >= today_str:
                current_reservations[reservation_date] = data
            else:
                past_reservations[reservation_date] = data

        tour_dict["current_reservations"] = current_reservations
        tour_dict["past_reservations"] = past_reservations
        tours_with_reservations.append(tour_dict)
        
    return render_template("guide_page.html", tours=tours_with_reservations)

# GUIDE PAGE (PUBLIC)
@app.route("/guide/<int:id>")
def public_guide(id):
    db_guide = users_dao.get_user_by_id(id)

    # check if the id exists in the db and if it has the guide role
    if not db_guide or db_guide["role"] != "guide":
        flash("Guide not found.", "warning")
        return redirect(url_for("home"))
    
    # get guide"s tours to display them in the template
    guide_tours = tours_dao.get_tours_by_guide(id)

    return render_template("guide_page_public.html", guide=db_guide, tours=guide_tours)


# GUIDE PUBLIC PAGE UPDATE
@app.route("/update_profile", methods=["POST"])
@login_required
def update_profile():
    if current_user.role != "guide":
        return redirect(url_for("home"))
        
    description = request.form.get("description")
    photo = request.files.get("profile_picture")
    
    # get existing user
    user_db = dict(users_dao.get_user_by_id(current_user.id))
    old_photo_path = user_db.get("profile_picture", "")
    destination_dir = os.path.join("static", "img", "guide_profiles")

    # ensure dir exists
    os.makedirs(destination_dir, exist_ok=True)

    photo_path = old_photo_path
    if photo and photo.filename != "":
        # simple timestamp string format
        timestamp = int(datetime.now().timestamp())
        ext = utility.get_filename_ext(photo.filename)
        filename = f"avatar_{current_user.id}_{timestamp}.{ext}"

        # define paths
        [system_path, photo_path] = utility.get_file_paths(destination_dir, filename)
        
        # convert to thumbnail and save
        img = Image.open(photo)
        utility.save_image_thumbnail(img, ext, system_path)

        # delete old photo
        if old_photo_path and old_photo_path != "":
            old_system_path = os.path.join("static", old_photo_path)
            if os.path.exists(old_system_path):
                os.remove(old_system_path)

    success = users_dao.update_user_profile(current_user.id, description, photo_path)
    if success:
        flash("Profile updated successfully!", "success")
    else:
        flash("Error while updating profile.", "danger")
        
    return redirect(url_for("guide_page"))

# ADMIN PAGE
@app.route("/admin_page")
@login_required
def admin_page():
    # only allow hardcoded admin account
    if current_user.role != "admin":
        flash("Administrator access required.", "danger")
        return redirect(url_for("home"))
        
    stats = users_dao.get_admin_stats()
    guides_db = users_dao.get_all_guides()
    
    guides_with_tours = []
    # get guide
    for guide in guides_db:
        guide_dict = dict(guide)
        
        # get tours for each guide
        tours = tours_dao.get_tours_by_guide(guide["id"])
        detailed_tours = []
        # get details for each tour
        for t in tours:
            detailed_tours.append(tours_dao.get_tour_details(t["id"]))
            
        guide_dict["tours"] = detailed_tours
        guides_with_tours.append(guide_dict)
        
    return render_template("admin_page.html", stats=stats, guides=guides_with_tours)


# CREATE TOUR PAGE
@app.route("/create_tour")
@login_required
def create_tour():
    # check if user is guide
    if current_user.role != "guide":
        flash("Only guides can create tours!", "danger")
        return redirect(url_for("home"))
    return render_template("create_tour.html", form_data=request.form)


# create tour logic
@app.route("/create_tour", methods=["POST"])
@login_required
def create_tour_post():
    # check if user is guide
    if current_user.role != "guide":
        flash("Only guides can create tours!", "danger")
        return redirect(url_for("home"))

    # convert the incoming form data to a dictionary
    form_data = request.form.to_dict()
    errors = {}

    title = request.form.get("title")
    language = request.form.get("language")
    duration = request.form.get("duration")
    meeting_point = request.form.get("meeting_point")
    max_participants = request.form.get("max_participants")
    description = request.form.get("description")
    
    # extract and clean up the list of stops, ignoring empty inputs
    stops = request.form.getlist("stops")
    new_stops = []
    for stop in stops:
        stripped = stop.strip()
        if stripped:
            new_stops.append(stripped)
    stops = new_stops

    form_data["stops"] = stops

    # extract selected days and pair them with their corresponding start times
    days = request.form.getlist("days")
    schedules = []
    for day in days:
        time_val = request.form.get("time_" + day)
        if time_val:
            schedules.append({"weekday": day, "start_time": time_val})

    form_data["days"] = days

    # extract the list of uploaded photos
    photos = request.files.getlist("tour_photos")

    def flash_error_message(message, type):
        errors[type] = message
        flash(message, "danger")

    # check that all required text fields have been filled
    for field in ["title", "language", "duration", "meeting_point", "max_participants", "description"]:
        value = request.form.get(field)
        if value is not None and value != "":
            continue
        formatted_name = field.replace("_", " ").capitalize()
        message = f"{formatted_name} was not provided."
        app.logger.error(message)
        flash_error_message(message, field)
        return render_template("create_tour.html", stops=stops, days=days, form_data=form_data, errors=errors)
    
    # validate that duration is a positive number
    if duration is not None and (not str(duration).isdigit() or int(duration) <= 0):
        message = "Duration must be a positive number in minutes."
        app.logger.error(message)
        flash_error_message(message, "duration")
        return render_template("create_tour.html", stops=stops, days=days, form_data=form_data, errors=errors)
    
    spoken_languages = {lang.strip() for lang in (current_user.languages or "").split(",") if lang.strip()}
    if language not in spoken_languages:
        app.logger.error("Language not matching guide's spoken languages.")
        flash_error_message("You can only create tours in languages you speak.", "language")
        return render_template("create_tour.html", stops=stops, days=days, form_data=form_data, errors=errors)
    
    # verify that the tour has the minimum required number of stops
    if len(stops) < 4:
        app.logger.error("Not enough stops provided.")
        flash_error_message("You must provide at least 4 itinerary stops.", "stops")
        return render_template("create_tour.html", stops=stops, days=days, form_data=form_data, errors=errors)
    
    # verify that at least one valid schedule day and time was provided
    if not schedules:
        app.logger.error("No schedule selected.")
        flash_error_message("You must select at least one day and time for the schedule.", "schedule")
        return render_template("create_tour.html", stops=stops, days=days, form_data=form_data, errors=errors)

    # check if the new schedule overlaps with any of the guide"s existing tours
    overlap_error = utility.check_guide_schedule_overlap(current_user.id, schedules, duration)
    if overlap_error:
        app.logger.error("Schedule overlap detected.")
        flash_error_message(overlap_error, "schedule")
        return render_template("create_tour.html", stops=stops, days=days, form_data=form_data, errors=errors)

    # verify exactly 5 promotional photos were uploaded
    for photo in photos:
        if photo is None or photo.filename == "":
            app.logger.error("Invalid number of photos.")
            flash_error_message("You must upload exactly 5 promotional photos.", "photos")
            return render_template("create_tour.html", stops=stops, days=days, form_data=form_data, errors=errors)
    photo_paths = utility.save_tour_photos(photos, current_user.id)
    
    # build the final dictionary to send to the database
    tour_data = {
        "guide_id": current_user.id,
        "title": title,
        "description": description,
        "meeting_point": meeting_point,
        "duration": duration,
        "language": language,
        "max_participants": max_participants,
        "photos": photo_paths,
        "stops": stops,
        "schedules": schedules
    }
    success = tours_dao.create_tour(tour_data)

    if success:
        app.logger.info("Tour created correctly.")
        flash("Tour published successfully!", "success")
        return redirect(url_for("home"))
    else:
        app.logger.error("Failed to create tour.")
        flash_error_message("Failed to create tour, please try again.", "general")
        return render_template("create_tour.html", stops=stops, days=days, form_data=form_data, errors=errors)

# tour reservation logic
@app.route("/tour_reservation", methods=["POST"])
@login_required
def tour_reservation():
    # check if the user is a participant
    if current_user.role != "participant":
        flash("Only participants can book tours.", "danger")
        return redirect(url_for("home"))
        
    # get the form data as a dictionary
    reservation_form = request.form.to_dict()
    
    tour_id = reservation_form["tour_id"]
    tour_date = reservation_form["tour_date"]
    num_people = int(reservation_form["num_people"])
    
    # get extra names, if field was filled
    if "extra_names" in reservation_form:
        extra_names = reservation_form["extra_names"].strip()
    else:
        extra_names = ""

    # check the number of people
    if num_people < 1 or num_people > 4:
        flash("A single reservation can only include 1 to 4 people.", "booking-error")
        return redirect(f"{url_for("single_tour", id=tour_id)}#booking-form")
        
    # handle extra names for group bookings
    if num_people > 1:
        provided_names = []
        raw_names = extra_names.replace("\n", ",").split(",")
        
        # strip whitespaces from each provided name
        for name in raw_names:
            stripped_name = name.strip()
            if stripped_name != "":
                provided_names.append(stripped_name)
                
        expected_extra = num_people - 1
        
        # check if the user provided the exact number of required extra names
        if len(provided_names) != expected_extra:
            flash(f"You selected {num_people} total people. Please provide exactly {expected_extra} extra name(s) separated by commas.", "booking-error")
            return redirect(f"{url_for("single_tour", id=tour_id)}#booking-form")

        extra_names = ", ".join(provided_names)
    else:
        extra_names = ""
    
    # get weekday from reservation date
    try:
        date_obj = datetime.strptime(tour_date, "%Y-%m-%d")
        weekday = utility.get_weekday(tour_date, app.logger, "Invalid weekday specified for the reservation.")
    except ValueError:
        return redirect(f"{url_for("single_tour", id=tour_id)}#booking-form")
        
    # get tour details from the database
    tour_db = tours_dao.get_tour_details(tour_id)
    
    valid_days = []
    for schedule in tour_db["schedules"]:
        valid_days.append(schedule["weekday"])
    
    # check if tour is scheduled on the selected day
    if weekday not in valid_days:
        flash(f"This tour does not run on {weekday}s. Please check the schedule and select a valid date.", "booking-error")
        return redirect(f"{url_for("single_tour", id=tour_id)}#booking-form")
        
    start_time_str = ""
    # get start time for the specific day
    for schedule in tour_db["schedules"]:
        if schedule["weekday"] == weekday:
            start_time_str = schedule["start_time"]
            break
            
    new_start_date = datetime.strptime(f"{tour_date} {start_time_str}", "%Y-%m-%d %H:%M")
    new_end_date = new_start_date + timedelta(minutes=tour_db["duration"])

    # check if the selected date is in the past
    now = datetime.now()
    if date_obj.date() < now.date():
        flash("You cannot book a tour in the past.", "booking-error")
        return redirect(f"{url_for("single_tour", id=tour_id)}#booking-form")

    # check if the tour starts in less than 24 hours
    if new_start_date < now + timedelta(hours=24):
        flash("You must book at least 24 hours before the tour starts.", "booking-error")
        return redirect(f"{url_for("single_tour", id=tour_id)}#booking-form")

    # get participant's existing bookings for the selected date
    participant_day_bookings = reservations_dao.get_participant_bookings_for_date(current_user.id, tour_date)
    
    # check new booking times with other reservations to prevent overlap
    for participant_booking in participant_day_bookings:
        existing_tour = tours_dao.get_tour_details(participant_booking["tour_id"])
        
        existing_start_str = ""
        for schedule in existing_tour["schedules"]:
            if schedule["weekday"] == weekday:
                existing_start_str = schedule["start_time"]
                break
                
        if existing_start_str != "":
            existing_start_date = datetime.strptime(f"{tour_date} {existing_start_str}", "%Y-%m-%d %H:%M")
            existing_end_date = existing_start_date + timedelta(minutes=existing_tour["duration"])
            
            # verify time overlaps
            if new_start_date < existing_end_date and new_end_date > existing_start_date:
                flash(f"Booking failed: Current reservation overlaps with your reservation for {existing_tour["title"]} ({existing_start_date.strftime("%H:%M")}-{existing_end_date.strftime("%H:%M")}).", "booking-error")
                return redirect(f"{url_for("single_tour", id=tour_id)}#booking-form")
            
    # get current number of bookings to check max participants
    current_bookings = reservations_dao.get_bookings_for_date(tour_id, tour_date)
    max_capacity = tour_db["max_participants"]
    
    # block the reservation if it exceeds maximum capacity
    if current_bookings + num_people > max_capacity:
        places_left = max_capacity - current_bookings
        flash(f"Booking failed: There are {places_left} places left for {tour_date}.", "booking-error")
        return redirect(f"{url_for("single_tour", id=tour_id)}#booking-form")
        
    # insert reservation data in the db
    reservation_data = {
        "participant_id": int(current_user.id),
        "tour_id": int(tour_id),
        "tour_date": tour_date,
        "num_people": num_people,
        "extra_names": extra_names
    }
    success = reservations_dao.add_reservation(reservation_data)
    if success:
        app.logger.info("Reservation created successfully")
        flash("Reservation confirmed! You can view it in your dashboard.", "success")
        return redirect(url_for("participant_page"))
    else:
        app.logger.error("Error creating the reservation: please try again!")
        flash("A database error occurred. Please try again.", "booking-error")
        return redirect(url_for("single_tour", id=tour_id) + "#booking-form")
    
# POST TOUR REPORT
@app.route("/submit_report", methods=["POST"])
@login_required
def submit_report():
    # check if the user is a guide
    if current_user.role != "guide":
        flash("Only guides can submit tour reports.", "danger")
        return redirect(url_for("home"))

    # get the form data as a dictionary
    report_form = request.form.to_dict()
    
    tour_id = report_form["tour_id"]
    tour_date = report_form["tour_date"]

    # check if tour has already happened
    try:
        report_date_obj = datetime.strptime(tour_date, "%Y-%m-%d").date()
        if report_date_obj > datetime.now().date():
            flash("You can only submit reports for tours that have already taken place.", "danger")
            return redirect(url_for("guide_page"))
    except ValueError:
        flash("Invalid date format.", "danger")
        return redirect(url_for("guide_page"))
    
    # check if the tour had any bookings on that date
    total_people = reservations_dao.get_bookings_for_date(tour_id, tour_date)
    if total_people == 0:
        flash("You can only submit reports for dates that had at least one reservation.", "warning")
        return redirect(url_for("guide_page"))

    # check for duplicate tour reports
    if tours_dao.check_report_exists(tour_id, tour_date):
        flash(f"A report for this tour on {tour_date} has already been submitted.", "warning")
        return redirect(url_for("guide_page"))

    actual_participants = report_form["actual_participants"]
    
    # get the uploaded photo safely
    if "evidence_photo" in request.files:
        photo = request.files["evidence_photo"]
    else:
        photo = None

    photo_path = ""
    destination_dir = os.path.join("static", "img", "evidence")
    if photo and photo.filename != "":
        # simple timestamp string format
        timestamp = int(datetime.now().timestamp())
        ext = utility.get_filename_ext(photo.filename)
        filename = f"report_{tour_id}_{timestamp}.{ext}"

        # define paths
        [system_path, photo_path] = utility.get_file_paths(destination_dir, filename)

        # convert to thumbnail and save
        img = Image.open(photo)
        utility.save_image_thumbnail(img, ext, system_path)
    else:
        app.logger.error("Evidence photo missing")
        flash("An evidence photo is required.", "danger")
        return redirect(url_for("guide_page"))

    # insert report data in db
    report_data = {
        "tour_id": int(tour_id),
        "tour_date": tour_date,
        "actual_participants": int(actual_participants),
        "evidence_photos": photo_path
    }
    success = tours_dao.add_tour_report(report_data)

    if success:
        app.logger.info("Tour report submitted successfully")
        flash("Tour report submitted successfully!", "success")
    else:
        app.logger.error("Error submitting the tour report: please try again!")
        flash("Failed to submit report. Please try again.", "danger")

    return redirect(url_for("guide_page"))


# cancel reservation logic
@app.route("/cancel_reservation", methods=["POST"])
@login_required
def cancel_reservation():
    # check if user is a participant
    if current_user.role != "participant":
        return redirect(url_for("home"))
    
    # get form data as a dictionary
    reservation_form = request.form.to_dict()
    reservation_id = reservation_form["reservation_id"]
    
    # get the reservation details from the database
    reservation = reservations_dao.get_reservation_by_id(reservation_id)

    def flash_error_message(message):
        app.logger.error(message)
        flash(message, "danger")

    # check that reservation exists and belongs to the current user
    if not reservation or reservation["participant_id"] != current_user.id:
        flash_error_message("Reservation not found or unauthorized access attempt.")
        return redirect(url_for("participant_page"))
    
    tour_date_str = reservation["tour_date"]
    
    # get the weekday
    try:
        weekday = utility.get_weekday(tour_date_str, app.logger, "Invalid weekday found for the reservation.")
    except ValueError:
        return redirect(url_for("participant_page"))

    # get tour details and get start time for weekday
    tour = tours_dao.get_tour_details(reservation["tour_id"])
    
    start_time_str = "00:00"
    for schedule in tour["schedules"]:
        if schedule["weekday"] == weekday:
            start_time_str = schedule["start_time"]
            break
    full_start_time_str = f"{tour_date_str} {start_time_str}"
    
    try:
        tour_datetime = datetime.strptime(full_start_time_str, "%Y-%m-%d %H:%M")
    except ValueError:
        flash_error_message("Error calculating tour start time.", "danger")
        return redirect(url_for("participant_page"))

    # compute difference between now and the tour start time
    time_difference = tour_datetime - datetime.now()
    
    # check if the cancellation is within 24 hour limit
    if time_difference >= timedelta(hours=24):
        reservations_dao.delete_reservation(reservation_id)
        app.logger.info(f"Reservation {reservation_id} cancelled successfully")
        flash("Reservation cancelled successfully.", "success")
    else:
        app.logger.error("Cancellation denied: inside 24h window")
        flash("Cancellation denied. The tour starts on " + tour_datetime.strftime("%b %d at %H:%M") + ", which is less than 24 hours away (or has passed).", "danger")

    return redirect(url_for("participant_page"))

# EDIT TOUR PAGE
@app.route("/edit_tour/<int:tour_id>")
@login_required
def edit_tour(tour_id):
    # check if user is guide
    if current_user.role != "guide":
        flash("Only guides can create tours!", "danger")
        return redirect(url_for("home"))

    # check if tour exists and belongs to current guide
    tour = tours_dao.get_tour_details(tour_id)
    if not tour or tour["guide_id"] != current_user.id:
        app.logger.error(f"Unauthorized access attempt to edit tour {tour_id}")
        flash("Unauthorized access.", "danger")
        return redirect(url_for("guide_page"))

    # check if there are upcoming reservations to lock essential info
    has_reservations = reservations_dao.check_if_reservations(tour_id)
    return render_template("edit_tour.html", tour=tour, has_reservations=has_reservations)

# edit tour logic
@app.route("/edit_tour/<int:tour_id>", methods=["POST"])
@login_required
def edit_tour_post(tour_id):
    # check if user is guide
    if current_user.role != "guide":
        flash("Only guides can create tours!", "danger")
        return redirect(url_for("home"))

    # check if tour exists and belongs to current guide
    tour = tours_dao.get_tour_details(tour_id)
    if not tour or tour["guide_id"] != current_user.id:
        app.logger.error(f"Unauthorized access attempt to edit tour {tour_id}")
        flash("Unauthorized access.", "danger")
        return redirect(url_for("guide_page"))
        
    # retrieve form data
    edit_form = request.form.to_dict()
    
    # non essential info (always editable)
    title = edit_form.get("title")
    description = edit_form.get("description")
    stops = request.form.getlist("stops")
    new_stops = []
    for stop in stops:
        stripped_stop = stop.strip()
        if stripped_stop != "":
            new_stops.append(stripped_stop)
    
    # essential info (locked if reservations exist)
    has_reservations = reservations_dao.check_if_reservations(tour_id)
    if has_reservations:
        language = tour["language"]
        duration = tour["duration"]
        meeting_point = tour["meeting_point"]
        max_participants = tour["max_participants"]
        schedules = tour["schedules"]

        edit_form["language"] = language
        edit_form["duration"] = duration
        edit_form["meeting_point"] = meeting_point
        edit_form["max_participants"] = max_participants
    else:
        language = edit_form.get("language")
        duration = edit_form.get("duration")
        meeting_point = edit_form.get("meeting_point")
        max_participants = edit_form.get("max_participants")
        
        days = request.form.getlist("days")
        schedules = []
        for day in days:
            time_val = request.form.get("time_" + day)
            if time_val:
                schedules.append({"weekday": day, "start_time": time_val})
            
    # process photos (only if new ones are uploaded)
    photo_paths = [] # keep existing photos
    for old_photo in tour["photos"]:
        photo_paths.append(old_photo["tour_photos"])

    photos = request.files.getlist("tour_photos")
    new_photo_paths = utility.save_tour_photos(photos, current_user.id)
    for photo_id, new_photo_path in enumerate(new_photo_paths):
        if new_photo_path == '':
            continue
        # remove old photo
        old_photo_path = photo_paths[photo_id]
        old_system_path = os.path.join("static", old_photo_path)
        if os.path.exists(old_system_path):
            os.remove(old_system_path)
        # update db with new photo
        photo_paths[photo_id] = new_photo_path
    
    # check if required fields are filled correctly
    utility.check_general_fields(
        ["title", "language", "duration", "meeting_point", "max_participants", "description"],
        edit_form, 
        url_for("edit_tour", tour_id=tour_id)
    )
        
    if len(new_stops) < 4:
        flash("You must provide at least 4 itinerary stops.", "danger")
        return redirect(url_for("edit_tour", tour_id=tour_id))
        
    if not schedules:
        flash("You must select at least one day and time for the schedule.", "danger")
        return redirect(url_for("edit_tour", tour_id=tour_id))

    # check if updated schedule overlaps (skip check if schedule is locked)
    if not has_reservations:
        overlap_error = utility.check_guide_schedule_overlap(current_user.id, schedules, duration, exclude_tour_id=tour_id)
        if overlap_error:
            flash(overlap_error, "danger")
            return redirect(url_for("edit_tour", tour_id=tour_id))
        
    # insert updated data in db
    updated_data = {
        "title": title,
        "language": language,
        "duration": duration,
        "meeting_point": meeting_point,
        "max_participants": max_participants,
        "description": description,
        "stops": new_stops,
        "schedules": schedules,
        "photos": photo_paths
    }
    
    if tours_dao.update_tour(tour_id, updated_data):
        app.logger.info(f"Tour {tour_id} + updated successfully")
        flash("Tour updated successfully", "success")
        return redirect(url_for("guide_page"))
    else:
        app.logger.error(f"Error updating tour {tour_id}")
        flash("Error updating tour", "danger")
            
    return render_template("edit_tour.html", tour=tour, has_reservations=has_reservations)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
