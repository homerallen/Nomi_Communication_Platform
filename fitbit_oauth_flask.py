from flask import Flask, redirect, request, session, url_for, jsonify
import requests
import base64
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Use a secure random key for session management

# Replace these with your Fitbit app credentials
CLIENT_ID = '23Q946'
CLIENT_SECRET = '004b36404ae05359bc334aad5dd6c152'
REDIRECT_URI = 'http://127.0.0.1:8000/callback'  # Update the redirect URI to match the new port
SCOPE = 'activity heartrate sleep weight oxygen_saturation'  # Adjust scopes as needed

def get_fitbit_data(endpoint_url):
    access_token = session.get('access_token')
    refresh_token = session.get('refresh_token')

    if not access_token:
        return redirect(url_for('login'))

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.get(endpoint_url, headers=headers)

    if response.status_code == 401:
        # Token might be expired, refresh
        token_url = "https://api.fitbit.com/oauth2/token"
        auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
        refresh_headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        refresh_data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        refresh_response = requests.post(token_url, headers=refresh_headers, data=refresh_data)

        if refresh_response.status_code == 200:
            new_token = refresh_response.json()
            session['access_token'] = new_token['access_token']
            session['refresh_token'] = new_token.get('refresh_token', refresh_token)
            headers["Authorization"] = f"Bearer {session['access_token']}"
            response = requests.get(endpoint_url, headers=headers)
        else:
            return redirect(url_for('login'))

    try:
        return response.json()
    except Exception as e:
        return {
            "error": "Failed to parse response.",
            "status_code": response.status_code,
            "text": response.text  # Add this to see raw response
        }

@app.route('/')
def home():
    return '<a href="/login">Login with Fitbit</a>'

@app.route('/login')
def login():
    auth_url = (
        f"https://api.fitbit.com/oauth2/authorize?response_type=code&"
        f"client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&"
        f"scope={SCOPE}&expires_in=31536000"
    )
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    token_url = "https://api.fitbit.com/oauth2/token"

    headers = {
        "Authorization": "Basic " + base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode(),
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "client_id": CLIENT_ID,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
        "code": code
    }

    response = requests.post(token_url, headers=headers, data=data)
    token_data = response.json()
    session['access_token'] = token_data.get('access_token')
    session['refresh_token'] = token_data.get('refresh_token')

    return redirect(url_for('get_historical_sleep_logs'))

@app.route('/get_historical_sleep_logs')
def get_historical_sleep_logs():
    start_date_str = '2024-12-30'
    end_date_str = datetime.now().strftime('%Y-%m-%d')
    user_id = "-"
    all_sleep_data = []
    current_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    max_range = timedelta(days=100)

    while current_date <= end_date:
        next_date = current_date + max_range
        if next_date > end_date:
            next_date = end_date

        url = f"https://api.fitbit.com/1.2/user/{user_id}/sleep/date/{current_date.strftime('%Y-%m-%d')}/{next_date.strftime('%Y-%m-%d')}.json"
        sleep_data = get_fitbit_data(url)

        if isinstance(sleep_data, dict) and 'sleep' in sleep_data:
            all_sleep_data.extend(sleep_data['sleep'])
        elif isinstance(sleep_data, dict) and 'errors' in sleep_data:
            return jsonify({"error": "Failed to retrieve sleep data", "details": sleep_data})
        elif not isinstance(sleep_data, redirect):  # Avoid adding redirect responses
            # Handle cases where the response might not be as expected
            print(f"Unexpected response for {current_date} to {next_date}: {sleep_data}")

        current_date = next_date + timedelta(days=1)

    return jsonify({"sleep_logs": all_sleep_data})

@app.route('/all_data')
def all_data():
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    user_id = "-"
    endpoints = {
        "SpO2": f"https://api.fitbit.com/1/user/-/spo2/date/2021-10-01/{datetime.now().strftime('%Y-%m-%d')}.json",
        "HeartRate": f"https://api.fitbit.com/1/user/{user_id}/activities/heart/date/{date}/1d.json",
        "Sleep": url_for('get_historical_sleep_logs')
    }

    results = {}
    for key, url in endpoints.items():
        if key == "Sleep":
            results[key] = redirect(url)
        else:
            results[key] = get_fitbit_data(url)

    return jsonify(results)

@app.route('/spo2')
def spo2():
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    user_id = "-"
    url = f"https://api.fitbit.com/1/user/{user_id}/spo2/date/{date}.json"
    return get_fitbit_data(url)

@app.route('/heartrate')
def heartrate():
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    user_id = "-"
    url = f"https://api.fitbit.com/1/user/{user_id}/activities/heart/date/{date}/1d.json"
    return get_fitbit_data(url)

@app.route('/sleep')
def sleep():
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    user_id = "-"
    url = f"https://api.fitbit.com/1.2/user/{user_id}/sleep/date/{date}.json"
    return get_fitbit_data(url)

if __name__ == '__main__':
    app.run(debug=True, port=8000)