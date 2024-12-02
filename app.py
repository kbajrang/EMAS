from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
import base64
import re
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from deadline import start_fetching_deadline  # Assuming this extracts deadlines

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Allows HTTP for OAuth

app = Flask(__name__)
app.secret_key = 'your_secret_key'

CLIENT_SECRETS_FILE = 'D:/ProjectMini/Clone/Email_Automation_Alert/credentials.json'

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/userinfo.email',
    'openid'
]

@app.route('/')
def index():
    """Homepage"""
    return render_template('index.html')

@app.route('/login')
def login():
    """Login with Google"""
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri='http://localhost:8080/callback'
    )
    authorization_url, state = flow.authorization_url(access_type='offline')
    session['state'] = state
    return redirect(authorization_url)

@app.route('/callback')
def oauth2callback():
    """OAuth2 callback"""
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri='http://localhost:8080/callback'
    )
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    session['credentials'] = credentials_to_dict(credentials)
    return redirect(url_for('read_emails'))

@app.route('/read_emails')
def read_emails():
    """Fetch and display emails"""
    credentials = session.get('credentials')
    if not credentials:
        return redirect(url_for('login'))

    try:
        credentials = Credentials(**credentials)
    except Exception:
        session.pop('credentials', None)
        return redirect(url_for('login'))

    service = build('gmail', 'v1', credentials=credentials)
    results = service.users().messages().list(userId='me', maxResults=10).execute()
    messages = results.get('messages', [])
    email_list = []

    if messages:
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            payload = msg.get('payload', {})
            headers = payload.get('headers', [])
            body = ""

            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        body = part['body']['data']
                        break
            else:
                body = payload.get('body', {}).get('data', '')

            if body:
                try:
                    body = base64.urlsafe_b64decode(body).decode('utf-8')
                except (TypeError, ValueError):
                    body = "Error decoding body."
                body = re.sub(r'http\S+', '', body)

            subject = next((header['value'] for header in headers if header['name'] == 'Subject'), 'No Subject')

            email_list.append({
                'id': message['id'],
                'subject': subject,
                'body': body,
                'snippet': msg.get('snippet', '')
            })

    extracted_deadlines = start_fetching_deadline(email_list)
    return render_template('emails.html', emails=extracted_deadlines)



    credentials = Credentials(**credentials)
    service = build('gmail', 'v1', credentials=credentials)
    results = service.users().messages().list(userId='me', maxResults=10).execute()
    messages = results.get('messages', [])
    email_list = []

    if messages:
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            payload = msg.get('payload', {})
            headers = payload.get('headers', [])
            body = ""

            if 'parts' in payload:  # Handle multipart messages
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        body = part['body']['data']
                        break
            else:
                body = payload.get('body', {}).get('data', '')

            if body:
                body = base64.urlsafe_b64decode(body).decode('utf-8')
                body = re.sub(r'http\S+', '', body)  # Remove URLs

            subject = next((header['value'] for header in headers if header['name'] == 'Subject'), 'No Subject')

            email_list.append({
                'id': message['id'],
                'subject': subject,
                'body': body,
                'snippet': msg.get('snippet', '')
            })

    # Pass emails to deadline extraction logic
    extracted_deadlines = start_fetching_deadline(email_list)
    return render_template('emails.html', emails=extracted_deadlines)

@app.route('/user_info')
def user_info():
    """Fetch and display user's profile and email information"""
    credentials = session.get('credentials')
    if not credentials:
        return redirect(url_for('login'))

    credentials = Credentials(**credentials)
    service = build('oauth2', 'v2', credentials=credentials)
    user_info = service.userinfo().get().execute()
    return render_template('user_info.html', user_info=user_info)

def credentials_to_dict(credentials):
    """Convert credentials to dictionary format"""
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

if __name__ == '__main__':
    app.run(debug=True, port=8080)
