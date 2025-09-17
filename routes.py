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
def home():
    # Public landing page (keep product or marketing content)
    # If you prefer the root to redirect to dashboard for logged-in users,
    # we can change this to detect session and redirect.
    return render_template('product.html')


@main.route('/dashboard')
def dashboard():
    # require login to view dashboard
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to access the dashboard.', 'error')
        return redirect(url_for('main.login', next=url_for('main.dashboard')))
    # fetch user profile for conditional rendering
    from dbkamp.db import get_connection
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    row = cur.fetchone()
    conn.close()
    user = dict(row) if row else None
    return render_template('dashboard.html', user=user)

@main.route('/upload', methods=['POST'])
def upload():
    # protect upload - only logged-in users
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to upload files.', 'error')
        return redirect(url_for('main.login'))
    # check user's company
    from dbkamp.db import get_connection
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT company FROM users WHERE id = ?', (user_id,))
    row = cur.fetchone()
    conn.close()
    company = row['company'] if row else None
    if not company:
        flash('Please complete your company information before uploading documents.', 'error')
        return redirect(url_for('main.complete_profile'))
    file = request.files.get('document')
    if not file:
        flash('No file selected.', 'error')
        return redirect(url_for('main.dashboard'))
    result = process_document(file)
    return render_template('dashboard.html', result=result)


@main.route('/upload', methods=['GET'])
def upload_get():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to access uploads.', 'error')
        return redirect(url_for('main.login'))
    # ensure company is set
    from dbkamp.db import get_connection
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT company FROM users WHERE id = ?', (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row or not row['company']:
        flash('Please complete your company information before uploading documents.', 'error')
        return redirect(url_for('main.complete_profile'))
    return render_template('upload.html')


@main.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        if not email or not password:
            flash('Email and password are required.', 'error')
            return render_template('signup.html', email=email)
        if confirm is None:
            # older forms may not include confirm field
            confirm = ''
        if password != confirm:
            flash('Passwords do not match. Please confirm your password.', 'error')
            return render_template('signup.html', email=email)
        success = create_user(email, password)
        if success:
            flash('Account created. Please log in.', 'success')
            return redirect(url_for('main.login'))
        else:
            flash('Email already exists.', 'error')
            return render_template('signup.html', email=email)
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


@main.route('/enterprise/request', methods=['GET', 'POST'])
def enterprise_request():
    if request.method == 'POST':
        company = request.form.get('company')
        contact_email = request.form.get('email')
        contact_name = request.form.get('name')
        plan = request.form.get('plan')
        message = request.form.get('message')
        if not company or not contact_email:
            flash('Company and contact email are required.', 'error')
            return render_template('enterprise_request.html', company=company, email=contact_email, name=contact_name, plan=plan, message=message)
        from dbkamp.db import create_enterprise_account
        create_enterprise_account(company, contact_email, contact_name, plan, message)
        flash('Thanks — we received your request. Our enterprise team will reach out shortly.', 'success')
        return redirect(url_for('main.enterprise'))
    return render_template('enterprise_request.html')


@main.route('/dashboard/enterprise-requests')
def dashboard_enterprise_requests():
    if not _require_login():
        return redirect(url_for('main.login', next=url_for('main.dashboard_enterprise_requests')))
    user_id = session.get('user_id')
    from dbkamp.db import get_connection
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT is_admin FROM users WHERE id = ?', (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row or not row['is_admin']:
        flash('Admin access required.', 'error')
        return redirect(url_for('main.dashboard'))
    from dbkamp.db import list_enterprise_accounts
    accounts = list_enterprise_accounts()
    return render_template('dashboard_enterprise_requests.html', accounts=accounts)


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


def _require_login():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to access this page.', 'error')
        return False
    return True


@main.route('/dashboard/general')
def dashboard_general():
    if not _require_login():
        return redirect(url_for('main.login', next=url_for('main.dashboard_general')))
    user_id = session.get('user_id')
    from dbkamp.db import get_connection
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    row = cur.fetchone()
    conn.close()
    user = dict(row) if row else None
    return render_template('dashboard_general.html', user=user)


@main.route('/dashboard/account')
def dashboard_account():
    if not _require_login():
        return redirect(url_for('main.login', next=url_for('main.dashboard_account')))
    user_id = session.get('user_id')
    from dbkamp.db import get_connection
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    row = cur.fetchone()
    conn.close()
    user = dict(row) if row else None
    # fetch tokens to display
    from dbkamp.db import list_api_tokens
    tokens = list_api_tokens(user_id)
    return render_template('dashboard_account.html', user=user, tokens=tokens)


@main.route('/dashboard/change-password', methods=['POST'])
def dashboard_change_password():
    if not _require_login():
        return redirect(url_for('main.login', next=url_for('main.dashboard_account')))
    user_id = session.get('user_id')
    old = request.form.get('old_password')
    new = request.form.get('new_password')
    confirm = request.form.get('confirm_password')
    if not old or not new:
        flash('Please provide both current and new password.', 'error')
        return redirect(url_for('main.dashboard_account'))
    # verify old password
    from dbkamp.db import get_connection, check_password_hash as _check
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT password FROM users WHERE id = ?', (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        flash('User not found.', 'error')
        return redirect(url_for('main.dashboard_account'))
    from werkzeug.security import check_password_hash
    if not check_password_hash(row['password'], old):
        flash('Current password is incorrect.', 'error')
        return redirect(url_for('main.dashboard_account'))
    if new != confirm:
        flash('New passwords do not match.', 'error')
        return redirect(url_for('main.dashboard_account'))
    from dbkamp.db import update_password
    ok = update_password(user_id, new)
    if ok:
        flash('Password updated.', 'success')
    else:
        flash('Unable to update password.', 'error')
    return redirect(url_for('main.dashboard_account'))


@main.route('/dashboard/notifications')
def dashboard_notifications():
    if not _require_login():
        return redirect(url_for('main.login', next=url_for('main.dashboard_notifications')))
    user_id = session.get('user_id')
    from dbkamp.db import get_user_preferences, update_notification_preferences
    if request.method == 'POST':
        notify_email = bool(request.form.get('notify_email'))
        notify_digest = request.form.get('notify_digest') or 'weekly'
        notify_webhook = request.form.get('notify_webhook') or ''
        ok = update_notification_preferences(user_id, notify_email, notify_digest, notify_webhook)
        if ok:
            flash('Notification preferences updated.', 'success')
        else:
            flash('Unable to update preferences.', 'error')
        return redirect(url_for('main.dashboard_notifications'))
    prefs = get_user_preferences(user_id)
    return render_template('dashboard_notifications.html', prefs=prefs)


@main.route('/dashboard/api')
def dashboard_api():
    if not _require_login():
        return redirect(url_for('main.login', next=url_for('main.dashboard_api')))
    user_id = session.get('user_id')
    from dbkamp.db import list_api_tokens
    tokens = list_api_tokens(user_id)
    return render_template('dashboard_api.html', tokens=tokens)


@main.route('/dashboard/api/create-token', methods=['POST'])
def dashboard_api_create_token():
    if not _require_login():
        return redirect(url_for('main.login', next=url_for('main.dashboard_api')))
    user_id = session.get('user_id')
    name = request.form.get('name') or 'token'
    # generate a random token to show once
    import secrets
    token_plain = secrets.token_urlsafe(32)
    from dbkamp.db import create_api_token, list_api_tokens
    create_api_token(user_id, name, token_plain)
    flash('API token created. Save it now; it will not be shown again.', 'success')
    # render page with token shown in the page once
    tokens = list_api_tokens(user_id)
    return render_template('dashboard_api.html', tokens=tokens, new_token=token_plain)


@main.route('/dashboard/api/revoke/<int:token_id>', methods=['POST'])
def dashboard_api_revoke(token_id):
    if not _require_login():
        return redirect(url_for('main.login', next=url_for('main.dashboard_api')))
    user_id = session.get('user_id')
    from dbkamp.db import revoke_api_token
    ok = revoke_api_token(token_id, user_id)
    if ok:
        flash('Token revoked.', 'success')
    else:
        flash('Unable to revoke token.', 'error')
    return redirect(url_for('main.dashboard_api'))


@main.route('/dashboard/imports')
def dashboard_imports():
    if not _require_login():
        return redirect(url_for('main.login', next=url_for('main.dashboard_imports')))
    user_id = session.get('user_id')
    from dbkamp.db import list_uploads_for_user
    uploads = list_uploads_for_user(user_id)
    return render_template('dashboard_imports.html', uploads=uploads)


@main.route('/dashboard/index', methods=['GET', 'POST'])
def dashboard_index():
    if not _require_login():
        return redirect(url_for('main.login', next=url_for('main.dashboard_index')))
    user_id = session.get('user_id')
    if request.method == 'POST':
        f = request.files.get('file')
        if not f:
            flash('No file uploaded.', 'error')
            return redirect(url_for('main.dashboard_imports'))
        # save to temp
        save_path = '/tmp/' + f.filename
        f.save(save_path)
        try:
            from models.retriever import index_csv
            n = index_csv(save_path)
            from dbkamp.db import record_upload
            record_upload(user_id, f.filename, 'success', message=f'Indexed {n} chunks', chunks_indexed=n)
            flash(f'Indexed {n} chunks from {f.filename}', 'success')
        except Exception as e:
            from dbkamp.db import record_upload
            record_upload(user_id, f.filename, 'error', message=str(e), chunks_indexed=0)
            flash('Indexing failed: ' + str(e), 'error')
        return redirect(url_for('main.dashboard_imports'))
    return redirect(url_for('main.dashboard_imports'))


@main.route('/dashboard/group')
def dashboard_group():
    if not _require_login():
        return redirect(url_for('main.login', next=url_for('main.dashboard_group')))
    # list groups the user can manage (for now show all)
    from dbkamp.db import list_groups
    groups = list_groups()
    return render_template('dashboard_group.html', groups=groups)


@main.route('/dashboard/group/create', methods=['POST'])
def dashboard_group_create():
    if not _require_login():
        return redirect(url_for('main.login', next=url_for('main.dashboard_group')))
    name = request.form.get('name')
    desc = request.form.get('description')
    if not name:
        flash('Group name is required.', 'error')
        return redirect(url_for('main.dashboard_group'))
    from dbkamp.db import create_group, add_group_member
    gid = create_group(name, desc)
    # add current user as admin
    add_group_member(gid, session.get('user_id'), role='admin')
    flash('Group created.', 'success')
    return redirect(url_for('main.dashboard_group'))


@main.route('/dashboard/group/<int:group_id>')
def dashboard_group_view(group_id):
    if not _require_login():
        return redirect(url_for('main.login', next=url_for('main.dashboard_group')))
    from dbkamp.db import list_group_members, list_group_projects
    members = list_group_members(group_id)
    projects = list_group_projects(group_id)
    return render_template('dashboard_group_view.html', group_id=group_id, members=members, projects=projects)


@main.route('/dashboard/group/<int:group_id>/add-member', methods=['POST'])
def dashboard_group_add_member(group_id):
    if not _require_login():
        return redirect(url_for('main.login', next=url_for('main.dashboard_group')))
    email = request.form.get('email')
    role = request.form.get('role') or 'member'
    if not email:
        flash('Email required to add member.', 'error')
        return redirect(url_for('main.dashboard_group_view', group_id=group_id))
    # find user by email
    from dbkamp.db import get_connection, add_group_member
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT id FROM users WHERE email = ?', (email,))
    row = cur.fetchone()
    conn.close()
    if not row:
        flash('User not found.', 'error')
        return redirect(url_for('main.dashboard_group_view', group_id=group_id))
    add_group_member(group_id, row['id'], role=role)
    flash('Member added.', 'success')
    return redirect(url_for('main.dashboard_group_view', group_id=group_id))


@main.route('/dashboard/group/<int:group_id>/link-project', methods=['POST'])
def dashboard_group_link_project(group_id):
    if not _require_login():
        return redirect(url_for('main.login', next=url_for('main.dashboard_group')))
    project_name = request.form.get('project_name')
    if not project_name:
        flash('Project name is required.', 'error')
        return redirect(url_for('main.dashboard_group_view', group_id=group_id))
    from dbkamp.db import link_project_to_group
    link_project_to_group(group_id, project_name)
    flash('Project linked to group.', 'success')
    return redirect(url_for('main.dashboard_group_view', group_id=group_id))


@main.route('/dashboard/project')
def dashboard_project():
    if not _require_login():
        return redirect(url_for('main.login', next=url_for('main.dashboard_project')))
    from dbkamp.db import list_projects
    projects = list_projects()
    return render_template('dashboard_project.html', projects=projects)


@main.route('/dashboard/project/create', methods=['POST'])
def dashboard_project_create():
    if not _require_login():
        return redirect(url_for('main.login', next=url_for('main.dashboard_project')))
    name = request.form.get('name')
    repo_url = request.form.get('repo_url')
    orchestration = request.form.get('orchestration')
    config = request.form.get('config')
    if not name:
        flash('Project name is required.', 'error')
        return redirect(url_for('main.dashboard_project'))
    from dbkamp.db import create_project
    pid = create_project(name, repo_url, orchestration, config)
    flash('Project created.', 'success')
    return redirect(url_for('main.dashboard_project_view', project_id=pid))


@main.route('/dashboard/project/<int:project_id>')
def dashboard_project_view(project_id):
    if not _require_login():
        return redirect(url_for('main.login', next=url_for('main.dashboard_project')))
    from dbkamp.db import get_project, list_issues, list_milestones
    proj = get_project(project_id)
    issues = list_issues(project_id)
    milestones = list_milestones(project_id)
    return render_template('dashboard_project_view.html', project=proj, issues=issues, milestones=milestones)


@main.route('/dashboard/project/<int:project_id>/issue', methods=['POST'])
def dashboard_project_create_issue(project_id):
    if not _require_login():
        return redirect(url_for('main.login', next=url_for('main.dashboard_project')))
    title = request.form.get('title')
    body = request.form.get('body')
    if not title:
        flash('Issue title is required.', 'error')
        return redirect(url_for('main.dashboard_project_view', project_id=project_id))
    from dbkamp.db import create_issue
    create_issue(project_id, title, body)
    flash('Issue created.', 'success')
    return redirect(url_for('main.dashboard_project_view', project_id=project_id))


@main.route('/dashboard/project/<int:project_id>/milestone', methods=['POST'])
def dashboard_project_create_milestone(project_id):
    if not _require_login():
        return redirect(url_for('main.login', next=url_for('main.dashboard_project')))
    title = request.form.get('title')
    due_date = request.form.get('due_date')
    if not title:
        flash('Milestone title is required.', 'error')
        return redirect(url_for('main.dashboard_project_view', project_id=project_id))
    from dbkamp.db import create_milestone
    create_milestone(project_id, title, due_date)
    flash('Milestone created.', 'success')
    return redirect(url_for('main.dashboard_project_view', project_id=project_id))


@main.route('/dashboard/project/<int:project_id>/config', methods=['POST'])
def dashboard_project_update_config(project_id):
    if not _require_login():
        return redirect(url_for('main.login', next=url_for('main.dashboard_project')))
    config = request.form.get('config')
    from dbkamp.db import get_connection
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('UPDATE projects SET config = ? WHERE id = ?', (config, project_id))
    conn.commit()
    conn.close()
    flash('Project configuration updated.', 'success')
    return redirect(url_for('main.dashboard_project_view', project_id=project_id))


@main.route('/dashboard/project/<int:project_id>/create-monitor', methods=['POST'])
def dashboard_project_create_monitor(project_id):
    if not _require_login():
        return redirect(url_for('main.login', next=url_for('main.dashboard_project')))
    email = request.form.get('monitor_email')
    name = request.form.get('monitor_name') or ''
    if not email:
        flash('Email is required to create a monitor.', 'error')
        return redirect(url_for('main.dashboard_project_view', project_id=project_id))
    # If the user exists, link; otherwise create a user with a random password and link
    from dbkamp.db import get_connection, create_user, add_project_member
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT id FROM users WHERE email = ?', (email,))
    row = cur.fetchone()
    if row:
        user_id = row['id']
        created = False
        password_plain = None
    else:
        import secrets
        password_plain = secrets.token_urlsafe(12)
        created = create_user(email, password_plain)
        # fetch id
        cur.execute('SELECT id FROM users WHERE email = ?', (email,))
        new = cur.fetchone()
        user_id = new['id'] if new else None
    conn.close()
    if not user_id:
        flash('Unable to create or find user.', 'error')
        return redirect(url_for('main.dashboard_project_view', project_id=project_id))
    add_project_member(project_id, user_id, role='monitor')
    if created and password_plain:
        flash('Monitor account created. Save the password now; it will not be shown again.', 'success')
        # render the project view and show the password once
        from dbkamp.db import get_project, list_issues, list_milestones, list_project_members
        proj = get_project(project_id)
        issues = list_issues(project_id)
        milestones = list_milestones(project_id)
        members = list_project_members(project_id)
        return render_template('dashboard_project_view.html', project=proj, issues=issues, milestones=milestones, members=members, new_monitor={'email': email, 'password': password_plain})
    flash('Monitor added to project.', 'success')
    return redirect(url_for('main.dashboard_project_view', project_id=project_id))


@main.route('/dashboard/environment')
def dashboard_environment():
    if not _require_login():
        return redirect(url_for('main.login', next=url_for('main.dashboard_environment')))
    # show all projects and let the user pick to manage environments
    from dbkamp.db import list_projects
    projects = list_projects()
    return render_template('dashboard_environment.html', projects=projects)


@main.route('/dashboard/project/<int:project_id>/environments')
def dashboard_project_environments(project_id):
    if not _require_login():
        return redirect(url_for('main.login', next=url_for('main.dashboard_project')))
    from dbkamp.db import get_project, list_environments, list_env_vars
    project = get_project(project_id)
    envs = list_environments(project_id)
    # load vars for the first environment for convenience
    vars_map = {}
    for e in envs:
        vars_map[e['id']] = list_env_vars(e['id'])
    return render_template('dashboard_environment_project.html', project=project, environments=envs, vars_map=vars_map)


@main.route('/dashboard/project/<int:project_id>/environments/create', methods=['POST'])
def dashboard_create_environment(project_id):
    if not _require_login():
        return redirect(url_for('main.login', next=url_for('main.dashboard_project')))
    name = request.form.get('name')
    target = request.form.get('target')
    if not name:
        flash('Environment name is required.', 'error')
        return redirect(url_for('main.dashboard_project_environments', project_id=project_id))
    from dbkamp.db import create_environment
    create_environment(project_id, name, target)
    flash('Environment created.', 'success')
    return redirect(url_for('main.dashboard_project_environments', project_id=project_id))


@main.route('/dashboard/environments/<int:env_id>/vars', methods=['POST'])
def dashboard_set_env_var(env_id):
    if not _require_login():
        return redirect(url_for('main.login'))
    key = request.form.get('key')
    value = request.form.get('value')
    if not key:
        flash('Key required.', 'error')
        return redirect(request.referrer or url_for('main.dashboard'))
    from dbkamp.db import set_env_var
    set_env_var(env_id, key, value)
    flash('Environment variable saved.', 'success')
    return redirect(request.referrer or url_for('main.dashboard'))


@main.route('/dashboard/security')
def dashboard_security():
    if not _require_login():
        return redirect(url_for('main.login', next=url_for('main.dashboard_security')))
    return render_template('dashboard_security.html')


@main.route('/dashboard/terminal')
def dashboard_terminal():
    if not _require_login():
        return redirect(url_for('main.login', next=url_for('main.dashboard_terminal')))
    user_id = session.get('user_id')
    from dbkamp.db import get_connection
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    row = cur.fetchone()
    conn.close()
    user = dict(row) if row else None
    return render_template('dashboard_terminal.html', user=user)


@main.route('/dashboard/admin')
def dashboard_admin():
    if not _require_login():
        return redirect(url_for('main.login', next=url_for('main.dashboard_admin')))
    user_id = session.get('user_id')
    from dbkamp.db import get_connection
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT is_admin FROM users WHERE id = ?', (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row or not row['is_admin']:
        flash('Admin access required.', 'error')
        return redirect(url_for('main.dashboard'))
    from dbkamp.db import list_audit_logs
    logs = list_audit_logs(200)
    return render_template('dashboard_admin.html', logs=logs)


@main.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.get_json() or {}
    prompt = data.get('message') or data.get('q')
    model = data.get('model') or 'mock'
    if not prompt:
        return {'error': 'no prompt provided'}, 400
    reply = ai_chat(prompt, model=model)
    return {'reply': reply}


@main.route('/api/ssh-keys', methods=['GET', 'POST'])
def api_ssh_keys():
    if not _require_login():
        return {'error': 'login required'}, 403
    user_id = session.get('user_id')
    from dbkamp.db import list_ssh_keys, add_ssh_key
    if request.method == 'POST':
        data = request.get_json() or {}
        title = data.get('title') or 'key'
        public_key = data.get('public_key')
        if not public_key:
            return {'error': 'public_key required'}, 400
        kid = add_ssh_key(user_id, title, public_key)
        return {'id': kid, 'title': title}
    # GET
    keys = list_ssh_keys(user_id)
    return {'keys': keys}


@main.route('/api/ssh-keys/revoke', methods=['POST'])
def api_ssh_keys_revoke():
    if not _require_login():
        return {'error': 'login required'}, 403
    data = request.get_json() or {}
    key_id = data.get('key_id')
    if not key_id:
        return {'error': 'key_id required'}, 400
    user_id = session.get('user_id')
    from dbkamp.db import remove_ssh_key
    ok = remove_ssh_key(int(key_id), user_id)
    if not ok:
        return {'error': 'unable to remove key'}, 400
    return {'ok': True}


@main.route('/api/security/graph')
def api_security_graph():
    # Return a small summary used to render an activity/incident graph in the UI
    if not _require_login():
        return {'error': 'login required'}, 403
    from dbkamp.db import list_audit_logs
    logs = list_audit_logs(200)
    # simple aggregation: count events by type (top 6)
    counts = {}
    for l in logs:
        t = l.get('event_type') or 'other'
        counts[t] = counts.get(t, 0) + 1
    # return top entries
    items = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:6]
    return {'items': [{'event_type': k, 'count': v} for k, v in items]}


@main.route('/api/exec', methods=['POST'])
def api_exec():
    # allow logged-in users to run a very small, safe whitelist of commands
    if not _require_login():
        return {'error': 'login required'}, 403
    import shlex, subprocess
    data = request.get_json() or {}
    cmd = (data.get('cmd') or '').strip()
    if not cmd:
        return {'error': 'no command provided'}, 400
    # whitelist of allowed base commands
    allowed = {'ls', 'pwd', 'whoami', 'echo', 'uname', 'uptime', 'date'}
    try:
        parts = shlex.split(cmd)
    except Exception as e:
        return {'error': 'invalid command format: ' + str(e)}, 400
    if not parts:
        return {'error': 'no command provided'}, 400
    base = parts[0]
    if base not in allowed:
        return {'error': f'command "{base}" not allowed'}, 403
    # force to not use shell and run with a timeout
    try:
        proc = subprocess.run(parts, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=8, text=True)
        return {'stdout': proc.stdout, 'stderr': proc.stderr, 'returncode': proc.returncode}
    except subprocess.TimeoutExpired:
        return {'error': 'command timed out'}, 500
    except Exception as e:
        return {'error': str(e)}, 500


@main.route('/api/generate', methods=['POST'])
def api_generate():
    data = request.get_json() or {}
    prompt = data.get('prompt') or data.get('q')
    model = data.get('model') or 'gpt2'
    if not prompt:
        return {'error': 'no prompt provided'}, 400
    try:
        from models.tts_and_text import text_generate
        out = text_generate(prompt, model_name=model)
        return {'result': out}
    except ImportError as e:
        return {'error': str(e)}, 500
    except Exception as e:
        return {'error': 'generation failed: ' + str(e)}, 500


@main.route('/api/tts', methods=['POST'])
def api_tts():
    data = request.get_json() or {}
    text = data.get('text')
    if not text:
        return {'error': 'no text provided'}, 400
    try:
        from models.tts_and_text import synthesize_speech
        wav = synthesize_speech(text)
        from flask import send_file
        import io
        return send_file(io.BytesIO(wav), mimetype='audio/wav', as_attachment=False, download_name='speech.wav')
    except ImportError as e:
        return {'error': str(e)}, 500
    except Exception as e:
        return {'error': 'TTS failed: ' + str(e)}, 500


@main.route('/api/employee', methods=['POST'])
def api_create_employee():
    data = request.get_json() or {}
    email = data.get('email')
    full_name = data.get('full_name')
    role = data.get('role')
    if not email:
        return {'error': 'email required'}, 400
    from dbkamp.db import create_employee
    eid = create_employee(email, full_name, role)
    return {'employee_id': eid}


@main.route('/api/activity', methods=['POST'])
def api_record_activity():
    data = request.get_json() or {}
    employee_id = data.get('employee_id')
    event_type = data.get('event_type')
    details = data.get('details')
    if not employee_id or not event_type:
        return {'error': 'employee_id and event_type required'}, 400
    from dbkamp.db import record_activity
    record_activity(employee_id, event_type, details)
    return {'ok': True}


@main.route('/api/activities')
def api_list_activities():
    emp = request.args.get('employee_id')
    from dbkamp.db import list_activities
    rows = list_activities(int(emp) if emp else None)
    return {'activities': rows}


@main.route('/api/generate-email', methods=['POST'])
def api_generate_email():
    data = request.get_json() or {}
    to = data.get('to')
    subject = data.get('subject') or 'A message from our team'
    context = data.get('context') or ''
    tone = data.get('tone') or 'professional'
    if not to:
        return {'error': 'recipient (to) is required'}, 400
    # Build a prompt for the AI chat/generator
    prompt = f"Write a {tone} email to {to}. Subject: {subject}. Context: {context}\n\nEmail:" 
    try:
        from models.ai_model import chat as ai_chat
        body = ai_chat(prompt, model='mock')
        return {'to': to, 'subject': subject, 'body': body}
    except Exception as e:
        return {'error': str(e)}, 500


@main.route('/api/create-token', methods=['POST'])
def api_create_token():
    # Create an API token and return the plain token in JSON (shown once)
    if not _require_login():
        return {'error': 'login required'}, 403
    data = request.get_json() or {}
    name = data.get('name') or data.get('label') or 'token'
    import secrets
    token_plain = secrets.token_urlsafe(32)
    user_id = session.get('user_id')
    try:
        from dbkamp.db import create_api_token
        create_api_token(user_id, name, token_plain)
        return {'token': token_plain, 'name': name}
    except Exception as e:
        return {'error': str(e)}, 500


@main.route('/api/stripe/create-checkout-session', methods=['POST'])
def api_stripe_create_checkout():
    # Create a Stripe Checkout Session for a selected plan
    data = request.get_json() or {}
    plan = data.get('plan') or 'pro'
    # Map plan to Stripe price IDs via config
    try:
        import stripe
    except Exception:
        return {'error': 'stripe library not installed'}, 500
    stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')
    price_map = {
        'pro': current_app.config.get('STRIPE_PRICE_PRO'),
        'team': current_app.config.get('STRIPE_PRICE_TEAM')
    }
    price = price_map.get(plan)
    if not price:
        return {'error': 'plan not configured'}, 400
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            mode='subscription',
            line_items=[{'price': price, 'quantity': 1}],
            success_url=request.host_url + 'dashboard?checkout=success',
            cancel_url=request.host_url + 'pricing?checkout=cancel'
        )
        return {'sessionId': session.id, 'url': session.url}
    except Exception as e:
        return {'error': str(e)}, 500


@main.route('/api/stripe/webhook', methods=['POST'])
def api_stripe_webhook():
    # Minimal webhook receiver. Configure STRIPE_WEBHOOK_SECRET in env for signature verification.
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = current_app.config.get('STRIPE_WEBHOOK_SECRET')
    try:
        import stripe
    except Exception:
        return {'error': 'stripe library not installed'}, 500
    stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')
    event = None
    try:
        if webhook_secret:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        else:
            event = stripe.Event.construct_from(request.get_json(), stripe.api_key)
    except Exception as e:
        return {'error': str(e)}, 400
    # Handle checkout.session.completed for example
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        # TODO: persist subscription and customer info in DB
        try:
            # Example: record audit log
            from dbkamp.db import record_audit
            record_audit('billing.checkout.completed', actor_user_id=session.get('client_reference_id'), details=str(session.get('id')))
        except Exception:
            pass
    return {'received': True}


@main.route('/api/revoke-token', methods=['POST'])
def api_revoke_token():
    if not _require_login():
        return {'error': 'login required'}, 403
    data = request.get_json() or {}
    token_id = data.get('token_id')
    if not token_id:
        return {'error': 'token_id required'}, 400
    user_id = session.get('user_id')
    try:
        from dbkamp.db import revoke_api_token
        ok = revoke_api_token(int(token_id), user_id)
        if ok:
            return {'ok': True}
        return {'error': 'unable to revoke'}, 400
    except Exception as e:
        return {'error': str(e)}, 500


@main.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_email', None)
    flash('Logged out.', 'success')
    return redirect(url_for('main.dashboard'))