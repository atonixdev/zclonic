from flask import Flask
from authlib.integrations.flask_client import OAuth
from routes import main


def create_app():
    app = Flask(__name__)

    # Load configuration from config.py
    app.config.from_pyfile('config.py')

    # Initialize OAuth
    oauth = OAuth(app)
    # Register common providers (config values must be provided in config.py or env)
    oauth.register('github', client_id=app.config.get('GITHUB_CLIENT_ID'), client_secret=app.config.get('GITHUB_CLIENT_SECRET'), access_token_url='https://github.com/login/oauth/access_token', authorize_url='https://github.com/login/oauth/authorize', api_base_url='https://api.github.com/', client_kwargs={'scope':'user:email'})
    oauth.register('gitlab', client_id=app.config.get('GITLAB_CLIENT_ID'), client_secret=app.config.get('GITLAB_CLIENT_SECRET'), access_token_url='https://gitlab.com/oauth/token', authorize_url='https://gitlab.com/oauth/authorize', api_base_url='https://gitlab.com/api/v4')
    oauth.register('linkedin', client_id=app.config.get('LINKEDIN_CLIENT_ID'), client_secret=app.config.get('LINKEDIN_CLIENT_SECRET'), access_token_url='https://www.linkedin.com/oauth/v2/accessToken', authorize_url='https://www.linkedin.com/oauth/v2/authorization', api_base_url='https://api.linkedin.com/v2', client_kwargs={'scope':'r_liteprofile r_emailaddress'})
    oauth.register('facebook', client_id=app.config.get('FACEBOOK_CLIENT_ID'), client_secret=app.config.get('FACEBOOK_CLIENT_SECRET'), access_token_url='https://graph.facebook.com/v10.0/oauth/access_token', authorize_url='https://www.facebook.com/v10.0/dialog/oauth', api_base_url='https://graph.facebook.com/')

    # Attach oauth instance to app for routes to use
    app.oauth = oauth

    # Register your blueprint
    app.register_blueprint(main)

    return app