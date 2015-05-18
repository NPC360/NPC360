from flask import session

from app import getUser as gU
from app import checkAuth as cA
#from app import getUser, checkAuth

from wtforms import Form, validators
from wtforms import StringField, TextAreaField, FileField, IntegerField
from wtforms import RadioField, BooleanField, HiddenField
from wtforms.fields.html5 import TelField


class SMSAuth(Form):
    def valid_auth_code(self, field):
        if field.data != cA(session.get('uid')):
            raise validators.ValidationError('Sorry, this is not the authentication code,')

    auth = IntegerField('Authentication Code', [
        validators.InputRequired(),
        validators.NumberRange(min=1000, max=9999, message="Not a valid authentication code."),
        valid_auth_code
    ])


class Phone(Form):
    def existing_mobile_check(self, field):
        if gU(field.data) is None:
            raise validators.StopValidation('Your mobile number is already in use.')

    mobile_number = TelField('Mobile Number', [
        validators.InputRequired(),
        existing_mobile_check
    ])


class Signup(Phone):
    def existing_email_check(self, field):
        if gU(field.data) is None:
            raise validators.StopValidation('Your email address is already in use.')

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
        validators.Email(),
        existing_email_check
    ])
    tz = HiddenField(validators=[], id="tz")


class FullSignup(Signup):
    # NOTE: Signup1.html does not display errors if validation is
    # added to these fields: team_work, ambitious, future_employment

    why_work = TextAreaField('Why do you want to work for Mercury Group?', [])
    work_history = TextAreaField('Relevant work history', [])

    s = 'Which best describes how you prefer to work?'
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

    s = 'Why did / will you leave your previous position?'
    leaving_choices = [
        (0, "Salary"),
        (1, "Lifestyle"),
        (2, "Unemployment"),
        (3, "Management"),
        (4, "Other")
    ]
    leaving = RadioField(s, choices=leaving_choices)

    animal = StringField('If you were an animal what would you be?', [])
    resume = FileField('Upload resume', [])

    s = 'Please contact me about future opportunities'
    future_employment = BooleanField(s, [])
