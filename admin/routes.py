from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from models import db, User, Chat, Message, CreditLog, SiteSetting
from forms import AdminUserForm, AdminSettingsForm
from werkzeug.security import generate_password_hash
from datetime import datetime, timezone

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Accès réservé aux administrateurs.', 'danger')
            return redirect(url_for('chat_page'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    total_credits = db.session.query(db.func.sum(User.credits)).scalar() or 0
    credits_used = CreditLog.query.filter_by(amount=-1).count()
    credits_given = CreditLog.query.filter(CreditLog.amount > 0).count()
    stats = {
        'users_total': User.query.count(),
        'users_active': User.query.filter_by(is_active=True).count(),
        'chats_total': Chat.query.count(),
        'messages_total': Message.query.count(),
        'total_credits': total_credits,
        'credits_used': credits_used,
        'credits_given': credits_given,
    }
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_chats = Chat.query.order_by(Chat.created_at.desc()).limit(5).all()
    return render_template('admin/dashboard.html', stats=stats, recent_users=recent_users, recent_chats=recent_chats)

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    page = request.args.get('page', 1, type=int)
    all_users = User.query.order_by(User.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/users.html', users=all_users)

@admin_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = AdminUserForm(obj=user)
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.is_admin = form.is_admin.data
        user.is_active = form.is_active.data
        if form.password.data:
            user.password_hash = generate_password_hash(form.password.data)
        db.session.commit()
        flash('Utilisateur mis à jour.', 'success')
        return redirect(url_for('admin.users'))
    return render_template('admin/user_edit.html', form=form, user=user)

@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        flash('Tu ne peux pas supprimer ton propre compte.', 'danger')
        return redirect(url_for('admin.users'))
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('Utilisateur supprimé.', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/chats')
@login_required
@admin_required
def chats():
    page = request.args.get('page', 1, type=int)
    all_chats = Chat.query.order_by(Chat.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/chats.html', chats=all_chats)

@admin_bp.route('/chats/view/<int:chat_id>')
@login_required
@admin_required
def view_chat(chat_id):
    chat = Chat.query.get_or_404(chat_id)
    messages = Message.query.filter_by(chat_id=chat_id).order_by(Message.created_at).all()
    return render_template('admin/chat_view.html', chat=chat, messages=messages)

@admin_bp.route('/chats/delete/<int:chat_id>', methods=['POST'])
@login_required
@admin_required
def delete_chat(chat_id):
    chat = Chat.query.get_or_404(chat_id)
    db.session.delete(chat)
    db.session.commit()
    flash('Conversation supprimée.', 'success')
    return redirect(url_for('admin.chats'))

@admin_bp.route('/credits')
@login_required
@admin_required
def credits():
    page = request.args.get('page', 1, type=int)
    logs = CreditLog.query.order_by(CreditLog.created_at.desc()).paginate(page=page, per_page=30, error_out=False)
    users = User.query.order_by(User.username).all()
    return render_template('admin/credits.html', logs=logs, users=users)

@admin_bp.route('/credits/add', methods=['POST'])
@login_required
@admin_required
def add_credits():
    user_id = request.form.get('user_id', type=int)
    amount = request.form.get('amount', type=int)
    reason = request.form.get('reason', 'Ajout manuel')
    if not user_id or not amount or amount < 1:
        flash('Montant invalide.', 'danger')
        return redirect(url_for('admin.credits'))
    user = User.query.get(user_id)
    if not user:
        flash('Utilisateur inconnu.', 'danger')
        return redirect(url_for('admin.credits'))
    user.credits += amount
    db.session.add(CreditLog(user_id=user_id, amount=amount, reason=reason))
    db.session.commit()
    flash(f'{amount} crédits ajoutés à {user.username}.', 'success')
    return redirect(url_for('admin.credits'))

@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    form = AdminSettingsForm()

    settings_map = {
        'site_name': ('Nom du site', 'AI Code Assistant'),
        'site_description': ('Description', 'Assistant IA de codage'),
        'ai_provider': ('Fournisseur IA', 'offline'),
        'openai_api_key': ('Clé API OpenAI', ''),
        'openai_model': ('Modèle IA', 'gpt-3.5-turbo'),
        'gemini_api_key': ('Clé API Gemini', ''),
        'gemini_model': ('Modèle Gemini', 'gemini-2.0-flash'),
        'welcome_message': ('Message de bienvenue', 'Bonjour ! Je suis ton assistant IA de codage. Pose-moi des questions sur Python, JavaScript, HTML/CSS, SQL, Git et plus encore.'),
        'system_prompt': ('Prompt système', ''),
    }

    if form.validate_on_submit():
        updates = {
            'site_name': form.site_name.data,
            'site_description': form.site_description.data,
            'ai_provider': form.ai_provider.data,
            'openai_api_key': form.openai_api_key.data,
            'openai_model': form.openai_model.data,
            'gemini_api_key': form.gemini_api_key.data,
            'gemini_model': form.gemini_model.data,
            'welcome_message': form.welcome_message.data,
            'system_prompt': form.system_prompt.data,
        }
        for key, value in updates.items():
            setting = SiteSetting.query.filter_by(key=key).first()
            if setting:
                setting.value = value
            else:
                db.session.add(SiteSetting(key=key, value=value))
        db.session.commit()
        flash('Paramètres enregistrés.', 'success')
        return redirect(url_for('admin.settings'))

    for key in settings_map:
        setting = SiteSetting.query.filter_by(key=key).first()
        default = settings_map[key][1]
        if hasattr(form, key) and setting:
            getattr(form, key).data = setting.value
        elif hasattr(form, key):
            getattr(form, key).data = default

    return render_template('admin/settings.html', form=form)
