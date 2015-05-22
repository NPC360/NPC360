from flask import session
from wtforms import Form, validators
from wtforms import StringField, TextAreaField, FileField, IntegerField
from wtforms import RadioField, BooleanField, HiddenField
from wtforms.fields.html5 import TelField

from user import getUser
from auth import checkAuth
from telUtil import *

class SMSAuth(Form):
    def valid_auth_code(self, field):
        if field.data != checkAuth(session.get('uid')):
            raise validators.ValidationError('Sorry, this is not the authentication code,')

    auth = IntegerField('Authentication Code', [
        validators.InputRequired(),
        validators.NumberRange(min=1000, max=9999, message="Not a valid authentication code."),
        valid_auth_code
    ])


class Phone(Form):
    def existing_mobile_check(self, field):
        if getUser(normalizeTel(field.data)) is not None:
            log.debug('that mobile # is already in use')
            raise validators.StopValidation('Your mobile number is already in use.')

    mobile_number = TelField('Mobile Number', [
        validators.InputRequired(),
        existing_mobile_check
    ])


class Signup(Phone):
    def existing_email_check(self, field):
        if getUser(field.data) is not None:
            log.debug('that email is already in use')
            raise validators.StopValidation('Your email address is already in use.')

    email = StringField('Email', [
        validators.InputRequired(),
        validators.Email(),
        existing_email_check
    ])

    first_name = StringField('First Name', [
        validators.InputRequired(),
        validators.length(min=2, max=50)
    ])

    last_name = StringField('Last Name', [
        validators.InputRequired(),
        validators.length(min=2, max=50)
    ])

    tz = HiddenField(validators=[], id="tz")


class FullSignup(Signup):
    # NOTE: Signup1.html does not display errors if validation is
    # added to these fields: team_work, ambitious, future_employment

    why_work = TextAreaField('Why do you want to work for Mercury Group?', [])
    work_history = TextAreaField('Relevant work history', [])

    r1 = 'Which best describes how you prefer to work?'
    team_work_choices = [
        (0, "Alone"),
        (1, "With a mix of both teams and alone"),
        (2, "With a team")
    ]
    team_work = RadioField(r1, choices=team_work_choices, validators=[validators.Required()])

    r2 = 'Would you describe yourself as ambitious?'
    ambition_choices = [
        (0, "Yes"),
        (1, "No")
    ]
    ambitious = RadioField(r2, choices=ambition_choices, validators=[validators.Required()])

    r3 = 'Why did / will you leave your previous position?'
    leaving_choices = [
        (0, "Salary"),
        (1, "Lifestyle"),
        (2, "Unemployment"),
        (3, "Management"),
        (4, "Other")
    ]
    leaving = RadioField(r3, choices=leaving_choices, validators=[validators.Required()])

    animal = StringField('If you were an animal what would you be?', [])
    resume = FileField('Upload resume', [])

    s = 'Please contact me about future opportunities'
    future_employment = BooleanField(s, [])
