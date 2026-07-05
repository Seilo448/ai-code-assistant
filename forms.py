from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, BooleanField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from models import User

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])

class RegistrationForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Mot de passe', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirmer le mot de passe', validators=[DataRequired(), EqualTo('password')])

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Ce nom d\'utilisateur est déjà pris.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Cet email est déjà utilisé.')

class ProfileForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])

class AdminUserForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    is_admin = BooleanField('Administrateur')
    is_active = BooleanField('Actif')
    password = PasswordField('Nouveau mot de passe (laisser vide pour ne pas changer)', validators=[Length(min=0, max=256)])

class AdminSettingsForm(FlaskForm):
    site_name = StringField('Nom du site', validators=[Length(max=200)])
    site_description = TextAreaField('Description du site', validators=[Length(max=500)])
    ai_provider = SelectField('Fournisseur IA', choices=[
        ('offline', 'Mode hors-ligne (gratuit, sans clé)'),
        ('gemini', 'Google Gemini (gratuit, clé requise)'),
        ('openai', 'OpenAI (payant, clé requise)'),
    ])
    openai_api_key = StringField('Clé API OpenAI')
    openai_model = SelectField('Modèle OpenAI', choices=[
        ('gpt-4o-mini', 'GPT-4o Mini (rapide, pas cher)'),
        ('gpt-4o', 'GPT-4o (puissant)'),
        ('gpt-3.5-turbo', 'GPT-3.5 Turbo'),
        ('gpt-4-turbo', 'GPT-4 Turbo'),
    ])
    gemini_api_key = StringField('Clé API Google Gemini')
    gemini_model = SelectField('Modèle Gemini', choices=[
        ('gemini-2.0-flash', 'Gemini 2.0 Flash (rapide)'),
        ('gemini-2.0-flash-lite', 'Gemini 2.0 Flash Lite (économique)'),
        ('gemini-1.5-flash', 'Gemini 1.5 Flash'),
        ('gemini-1.5-pro', 'Gemini 1.5 Pro (puissant)'),
    ])
    welcome_message = TextAreaField('Message de bienvenue')
    system_prompt = TextAreaField('Prompt système de l\'IA', validators=[Length(max=2000)])
