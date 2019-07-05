import wtforms

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired


class UploadForm(FlaskForm):
    """ Form used to upload the results of kernel tests. """

    username = wtforms.TextField("Username", default="anon")
    test_result = FileField("Result file", validators=[FileRequired()])


class ReleaseForm(FlaskForm):
    """ Form used to create or edit release in the database. """

    version = wtforms.IntegerField(
        "Release number <span class='error'>*</span>",
        validators=[wtforms.validators.Required()],
    )
    support = wtforms.SelectField(
        "Support <span class='error'>*</span>",
        validators=[wtforms.validators.Required()],
        choices=[
            ("RAWHIDE", "Rawhide"),
            ("TEST", "Test"),
            ("RELEASE", "Release"),
            ("RETIRED", "Retired"),
        ],
    )
