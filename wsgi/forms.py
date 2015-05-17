from wtforms import Form, validators
from wtforms import StringField, TextAreaField, FileField
from wtforms import RadioField, BooleanField, HiddenField
from wtforms.fields.html5 import TelField


class Signup(Form):
    first_name = StringField('First Name', [
        validators.InputRequired(),
        validators.length(min=2, max=50)
    ])
    last_name = StringField('Last Name', [
        validators.InputRequired(),
        validators.length(min=2, max=50)
    ])
    email = StringField('Email', [
        validators.InputRequired(),
        validators.Email()
    ])
    mobile_number = TelField('Mobile Number', [
        validators.InputRequired()
    ])
    tz = HiddenField([])


class FullSignup(Signup):
    # NOTE: Signup1.html does not display errors if validation is
    # added to these fields: team_work, ambitious, future_employment

    why_work = TextAreaField('Why do you want to work for Mercury Group', [])
    work_history = TextAreaField('Relevant work history', [])

    s = 'Which best describes how you prefer to work'
    team_work_choices = [
        (1, "Alone"),
        (2, "With a mix of both teams and alone"),
        (3, "With a team")
    ]
    team_work = RadioField(s, choices=team_work_choices)

    s = 'Would you describe yourself as ambitious?'
    ambition_choices = [
        (0, "Yes"),
        (1, "No")
    ]
    ambitious = RadioField(s, choices=ambition_choices)
    animal = TextAreaField('If you were an animal what would you be?', [])
    resume = FileField('Upload resume', [])

    s = 'I am happy to be contacted about future opportunities'
    future_employment = BooleanField(s, [])
