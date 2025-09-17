import os

# Basic app configuration
SECRET_KEY = os.environ.get('ZCLONIC_SECRET_KEY', 'your-secure-key')
UPLOAD_FOLDER = os.environ.get('ZCLONIC_UPLOAD_FOLDER', '/path/to/uploads')

# OAuth client credentials (recommended: set via environment variables)
# Example: export GITHUB_CLIENT_ID=your_id
GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID')
GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET')
GITLAB_CLIENT_ID = os.environ.get('GITLAB_CLIENT_ID')
GITLAB_CLIENT_SECRET = os.environ.get('GITLAB_CLIENT_SECRET')
LINKEDIN_CLIENT_ID = os.environ.get('LINKEDIN_CLIENT_ID')
LINKEDIN_CLIENT_SECRET = os.environ.get('LINKEDIN_CLIENT_SECRET')
FACEBOOK_CLIENT_ID = os.environ.get('FACEBOOK_CLIENT_ID')
FACEBOOK_CLIENT_SECRET = os.environ.get('FACEBOOK_CLIENT_SECRET')