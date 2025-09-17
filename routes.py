from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models.ai_model import process_document
from dbkamp.db import init_db, create_user, authenticate_user, update_user_profile
from models.ai_model import chat as ai_chat
from datetime import datetime
from flask import current_app

# ensure DB exists when blueprint is imported
init_db()

main = Blueprint('main', __name__)


@main.app_context_processor
def inject_globals():
    # provide year and simple user info to templates
    return {
        'current_year': datetime.utcnow().year,
    }

@main.route('/')
def dashboard():
    # require login to view dashboard
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to access the dashboard.', 'error')
        return redirect(url_for('main.login', next=url_for('main.dashboard')))
    return render_template('dashboard.html')

@main.route('/upload', methods=['POST'])
def upload():
    # protect upload - only logged-in users
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to upload files.', 'error')
        return redirect(url_for('main.login'))
    file = request.files['document']
    result = process_document(file)
    return render_template('dashboard.html', result=result)


@main.route('/upload', methods=['GET'])
def upload_get():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to access uploads.', 'error')
        return redirect(url_for('main.login'))
    return render_template('upload.html')


@main.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if not email or not password:
            flash('Email and password are required.', 'error')
            return render_template('signup.html')
        success = create_user(email, password)
        if success:
            flash('Account created. Please log in.', 'success')
            return redirect(url_for('main.login'))
        else:
            flash('Email already exists.', 'error')
            return render_template('signup.html')
    return render_template('signup.html')


@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = authenticate_user(email, password)
        if user:
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            flash('Logged in successfully.', 'success')
            # If profile incomplete, redirect to complete profile
            if not user.get('full_name') or not user.get('company'):
                return redirect(url_for('main.complete_profile'))
            # Respect optional `next` param so we can redirect to dashboard or original page
            next_url = request.args.get('next') or request.form.get('next')
            if next_url:
                return redirect(next_url)
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid credentials.', 'error')
            return render_template('login.html')
    return render_template('login.html')


@main.route('/login/<provider>')
def oauth_login(provider):
    # start oauth login flow
    oauth = current_app.oauth
    if provider not in oauth._registry:
        flash('Unknown OAuth provider.', 'error')
        return redirect(url_for('main.login'))
    redirect_uri = url_for('main.oauth_callback', provider=provider, _external=True)
    return oauth.create_client(provider).authorize_redirect(redirect_uri)


@main.route('/auth/<provider>/callback')
def oauth_callback(provider):
    oauth = current_app.oauth
    client = oauth.create_client(provider)
    if not client:
        flash('OAuth client not configured.', 'error')
        return redirect(url_for('main.login'))
    token = client.authorize_access_token()
    if not token:
        flash('Authentication failed.', 'error')
        return redirect(url_for('main.login'))
    # fetch basic profile information depending on provider
    profile = {}
    if provider == 'github':
        profile = client.get('user').json()
        email = profile.get('email') or (client.get('user/emails').json()[0].get('email') if client.get('user/emails') else None)
    elif provider == 'gitlab':
        profile = client.get('user').json()
        email = profile.get('email')
    elif provider == 'linkedin':
        # LinkedIn requires separate endpoints for email and profile
        profile = client.get('me').json()
        email_resp = client.get('emailAddress?q=members&projection=(elements*(handle~))')
        email = None
        try:
            email = email_resp.json().get('elements', [])[0].get('handle~', {}).get('emailAddress')
        except Exception:
            email = None
    elif provider == 'facebook':
        profile = client.get('me?fields=id,name,email').json()
        email = profile.get('email')
    else:
        email = None

    if not email:
        flash('Could not retrieve email from provider. Please sign up with email/password.', 'error')
        return redirect(url_for('main.signup'))

    # If user exists, log them in; otherwise create an account (random password)
    user = authenticate_user(email, '')
    # authenticate_user expects a password; instead we'll check existence directly
    from dbkamp.db import get_connection
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE email = ?', (email,))
    row = cur.fetchone()
    conn.close()
    if row:
        session['user_id'] = row['id']
        session['user_email'] = row['email']
        flash('Logged in with ' + provider.capitalize(), 'success')
        return redirect(url_for('main.dashboard'))
    else:
        # create user with a random password placeholder
        import secrets
        pw = secrets.token_urlsafe(16)
        created = create_user(email, pw)
        if created:
            # fetch new user id
            conn = get_connection()
            cur = conn.cursor()
            cur.execute('SELECT * FROM users WHERE email = ?', (email,))
            new = cur.fetchone()
            conn.close()
            session['user_id'] = new['id']
            session['user_email'] = new['email']
            flash('Account created via ' + provider.capitalize(), 'success')
            return redirect(url_for('main.complete_profile'))
        else:
            flash('Unable to create account.', 'error')
            return redirect(url_for('main.signup'))


@main.route('/resources')
def resources():
    return render_template('resources.html')


@main.route('/Enterprise')
def enterprise():
    return render_template('enterprise.html')


@main.route('/pricing')
def pricing():
    return render_template('pricing.html')


@main.route('/Devs')
def devs():
    return render_template('devs.html')


@main.route('/solutions')
def solutions():
    return render_template('solutions.html')


@main.route('/investors')
def investors():
    return render_template('investors.html')


@main.route('/partners')
def partners():
    return render_template('partners.html')


@main.route('/editorial')
def editorial():
    return render_template('editorial.html')


@main.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # simple contact handler - in real app we'd persist/send email
        flash('Thanks — we received your message. Our team will reply shortly.', 'success')
        return redirect(url_for('main.dashboard'))
    return render_template('contact.html')


@main.route('/product')
def product():
    return render_template('product.html')


@main.route('/complete-profile', methods=['GET', 'POST'])
def complete_profile():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in first.', 'error')
        return redirect(url_for('main.login'))
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        company = request.form.get('company')
        phone = request.form.get('phone')
        ok = update_user_profile(user_id, full_name=full_name, company=company, phone=phone)
        if ok:
            flash('Profile updated.', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Unable to update profile.', 'error')
    return render_template('complete_profile.html')


@main.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.get_json() or {}
    prompt = data.get('message') or data.get('q')
    model = data.get('model') or 'mock'
    if not prompt:
        return {'error': 'no prompt provided'}, 400
    reply = ai_chat(prompt, model=model)
    return {'reply': reply}


@main.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_email', None)
    flash('Logged out.', 'success')
    return redirect(url_for('main.dashboard'))