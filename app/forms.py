from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import (
    BooleanField,
    EmailField,
    HiddenField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional


class RegisterForm(FlaskForm):
    username = StringField("Commander Name", validators=[DataRequired(), Length(min=3, max=80)])
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Create Account")


class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember me")
    submit = SubmitField("Login")


class PrivacyForm(FlaskForm):
    is_public = BooleanField("Make colony public")
    submit = SubmitField("Save Privacy")


class DiscussionPostForm(FlaskForm):
    title = StringField("Post title", validators=[DataRequired(), Length(min=3, max=120)])
    content = TextAreaField("Strategy notes", validators=[DataRequired(), Length(min=5, max=1200)])
    image = FileField(
        "Optional colony screenshot",
        validators=[FileAllowed(["png", "jpg", "jpeg", "gif", "webp"], "Images only.")],
    )
    offer_oxygen = IntegerField("Oxygen offer", default=0, validators=[Optional(), NumberRange(min=0, max=100000)])
    offer_water = IntegerField("Water offer", default=0, validators=[Optional(), NumberRange(min=0, max=100000)])
    offer_minerals = IntegerField("Mineral offer", default=0, validators=[Optional(), NumberRange(min=0, max=100000)])
    submit = SubmitField("Post Strategy")


class CommentForm(FlaskForm):
    post_id = HiddenField("Post ID", validators=[DataRequired()])
    content = TextAreaField("Comment", validators=[DataRequired(), Length(min=2, max=500)])
    submit = SubmitField("Add Comment")


class RewardExchangeForm(FlaskForm):
    exchange_type = SelectField(
        "Exchange type",
        choices=[
            ("offer", "Offer resources"),
            ("request", "Request resources"),
        ],
        validators=[DataRequired()],
    )
    resource_type = SelectField(
        "Resource",
        choices=[
            ("oxygen", "oxygen"),
            ("water", "water"),
            ("minerals", "minerals"),
        ],
        validators=[DataRequired()],
    )
    amount = IntegerField("Amount", default=25, validators=[DataRequired(), NumberRange(min=1, max=100000)])
    receiver_username = StringField("Receiver for offers", validators=[Optional(), Length(max=80)])
    submit = SubmitField("Create Exchange")


class ThanksMessageForm(FlaskForm):
    exchange_id = HiddenField("Exchange ID", validators=[DataRequired()])
    message = TextAreaField("Thanks message", validators=[DataRequired(), Length(min=2, max=240)])
    submit = SubmitField("Send Thanks")
