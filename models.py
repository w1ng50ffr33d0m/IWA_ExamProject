from flask_login import UserMixin

class User(UserMixin):
    def __init__ (self, id, first_name, last_name, email, password, role, languages, description, profile_picture):
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.password = password
        self.role = role
        self.languages = languages
        self.description = description
        self.profile_picture = profile_picture

    @classmethod
    def load_from_database(cls, database_record):
        # create user instance with data taken from database
        return cls(
            id = database_record["id"],
            first_name = database_record["first_name"],
            last_name = database_record["last_name"],
            email = database_record["email"],
            password = database_record["password"],
            role = database_record["role"],
            languages = database_record["languages"],
            description = database_record["description"],
            profile_picture = database_record["profile_picture"]
        )