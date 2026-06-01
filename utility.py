# IMPORT MODULES
import os
from datetime import datetime, timedelta
from flask import redirect, flash

from PIL import Image, ImageOps

import tours_dao
import threading
from pathlib import Path

# DEFINITIONS OF UTILITY FUNCTIONS USED IN app.py

def check_guide_schedule_overlap(guide_id, new_schedules, duration, exclude_tour_id=None):
    existing_schedules = tours_dao.get_all_guide_schedules(guide_id, exclude_tour_id)

    for new_sched in new_schedules:
        new_start = datetime.strptime(new_sched["start_time"], "%H:%M")
        new_end = new_start + timedelta(minutes=int(duration))

        for ext_sched in existing_schedules:
            if new_sched["weekday"] == ext_sched["weekday"]:
                ext_start = datetime.strptime(ext_sched["start_time"], "%H:%M")
                ext_end = ext_start + timedelta(minutes=int(ext_sched["duration"]))

                if new_start < ext_end and new_end > ext_start:
                    return f"Schedule overlap on {new_sched['weekday']}s with your existing tour \"{ext_sched['title']}\"."
    return None

def get_filename_ext(filename):
    return filename.split(".")[-1]

def get_file_paths(system_dir, filename):
    dir = Path(system_dir)
    system_path = dir.joinpath(filename)
    db_path = Path(*system_path.parts[1:])
    return [str(system_path), db_path.as_posix()]

def save_image_thumbnail(img, ext, system_path, max_size=(1000,1000), quality=85):
    img.thumbnail(max_size, Image.Resampling.BILINEAR)
    if ext in {"jpg", "jpeg"}:
        img.save(system_path, format="JPEG", quality=quality, optimize=True)
    else:
        img.save(system_path, format="PNG", optimize=True)

def save_tour_photo(uploaded_file, destination_dir, prefix):
    os.makedirs(destination_dir, exist_ok=True)

    # simple timestamp string format
    timestamp = int(datetime.now().timestamp())
    ext = get_filename_ext(uploaded_file.filename)
    filename = f"{prefix}_{timestamp}.{ext}"

    # define paths
    [system_path, photo_path] = get_file_paths(destination_dir, filename)

    # convert to thumbnail and save
    img = Image.open(uploaded_file)
    save_image_thumbnail(img, ext, system_path, max_size=(1600,1600))

    return photo_path

def save_tour_photos(valid_photos, user_id):
    photo_paths = {}
    save_dir = os.path.join("static", "img", "tours")

    # save images with multiple threads, speeds up response times
    def save_and_resize_image(img_file, photo_id, save_dir, prefix, photo_paths):
        if img_file.filename == '':
            photo_paths[photo_id] = ''
            return
        photo_path = save_tour_photo(
            img_file,
            save_dir,
            prefix
        )
        photo_paths[photo_id] = photo_path

    threads = []
    for photo_id, img_file in enumerate(valid_photos):
        t = threading.Thread(target=save_and_resize_image, args=(img_file, photo_id, save_dir, f"tour-{user_id}-{photo_id}", photo_paths))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

    result = []
    for photo_id in range(0, len(valid_photos)):
        result.append(photo_paths[photo_id])
    return result

def get_weekday(tour_date, logger, error):
    try:
        return datetime.strptime(tour_date, "%Y-%m-%d").strftime("%A")
    except ValueError:
        logger.error(error)
        flash(error, "danger")
        raise ValueError(error)

def check_general_fields(fields, form, redirect_url):
    for field in fields:
        value = form.get(field)
        if value is not None and value != "":
            continue
        field_name = field.capitalize().replace("_", " ")
        flash(f"{field_name} is required.", "danger")
        return redirect(redirect_url)

