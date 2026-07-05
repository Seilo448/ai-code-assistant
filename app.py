import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_login import LoginManager, login_required, current_user
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    from models import db, User, Chat, Message, SiteSetting
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Veuillez te connecter pour accéder à cette page.'
    login_manager.init_app(app)

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.is_json:
            return jsonify({'error': 'Session expirée. Reconnecte-toi.'}), 401
        return redirect(url_for('auth.login'))

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from auth.routes import auth_bp
    from admin.routes import admin_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    with app.app_context():
        db.create_all()
        if not User.query.filter_by(is_admin=True).first():
            admin = User(
                username='admin',
                email='admin@example.com',
                password_hash='scrypt:32768:8:1$YjW9wU4vF0a1b2c3$abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef12345678',
                is_admin=True
            )
            from werkzeug.security import generate_password_hash
            admin.password_hash = generate_password_hash('admin123')
            db.session.add(admin)
            db.session.commit()

    from ai.engine import AIEngine
    app.ai_engine = AIEngine(app)

    @app.context_processor
    def inject_settings():
        settings = {}
        for s in SiteSetting.query.all():
            settings[s.key] = s.value
        return dict(site_settings=settings)

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('chat_page'))
        return render_template('index.html')

    @app.route('/chat', endpoint='chat_page')
    @login_required
    def chat():
        chats = Chat.query.filter_by(user_id=current_user.id).order_by(Chat.updated_at.desc()).all()
        return render_template('chat.html', chats=chats)

    @app.route('/api/chat/new', methods=['POST'])
    @login_required
    def new_chat():
        chat = Chat(user_id=current_user.id)
        db.session.add(chat)
        db.session.commit()
        return jsonify({'id': chat.id, 'title': chat.title})

    @app.route('/api/user/credits')
    @login_required
    def user_credits():
        return jsonify({'credits': current_user.credits})

    @app.route('/api/chat/<int:chat_id>/message', methods=['POST'])
    @login_required
    def send_message(chat_id):
        chat = Chat.query.get_or_404(chat_id)
        if chat.user_id != current_user.id and not current_user.is_admin:
            return jsonify({'error': 'Accès interdit'}), 403

        data = request.get_json()
        user_message = data.get('message', '').strip()
        if not user_message:
            return jsonify({'error': 'Message vide'}), 400

        if current_user.credits < 1 and not current_user.is_admin:
            return jsonify({'error': 'Crédits insuffisants. Contacte l\'administrateur pour en obtenir.'}), 403

        try:
            ai_content = app.ai_engine.generate_response(chat_id, user_message)
            formatted = app.ai_engine.format_response(ai_content)
            if not current_user.is_admin:
                current_user.credits -= 1
                from models import CreditLog
                db.session.add(CreditLog(user_id=current_user.id, amount=-1, reason='Message envoyé'))
                db.session.commit()
            return jsonify({'response': ai_content, 'formatted': formatted, 'credits_remaining': current_user.credits})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/chat/<int:chat_id>/messages')
    @login_required
    def get_messages(chat_id):
        chat = Chat.query.get_or_404(chat_id)
        if chat.user_id != current_user.id and not current_user.is_admin:
            return jsonify({'error': 'Accès interdit'}), 403

        messages = Message.query.filter_by(chat_id=chat_id).order_by(Message.created_at).all()
        return jsonify([{
            'role': m.role,
            'content': m.content,
            'formatted': app.ai_engine.format_response(m.content),
            'created_at': m.created_at.isoformat()
        } for m in messages])

    @app.route('/api/chat/<int:chat_id>/delete', methods=['DELETE'])
    @login_required
    def delete_chat(chat_id):
        chat = Chat.query.get_or_404(chat_id)
        if chat.user_id != current_user.id and not current_user.is_admin:
            return jsonify({'error': 'Accès interdit'}), 403
        db.session.delete(chat)
        db.session.commit()
        return jsonify({'success': True})

    @app.route('/api/chat/<int:chat_id>/rename', methods=['PUT'])
    @login_required
    def rename_chat(chat_id):
        chat = Chat.query.get_or_404(chat_id)
        if chat.user_id != current_user.id:
            return jsonify({'error': 'Accès interdit'}), 403
        data = request.get_json()
        chat.title = data.get('title', chat.title)[:200]
        db.session.commit()
        return jsonify({'success': True})

    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
