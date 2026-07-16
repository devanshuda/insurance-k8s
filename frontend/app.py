from flask import Flask, render_template, request, redirect, url_for
import requests
import os

app = Flask(__name__)

API_URL = os.getenv("API_URL", "http://insurance-api-service:8000")

@app.route('/')
def catalog():
    return render_template('catalog.html')

@app.route('/form/<item>')
def form(item):
    return render_template('form.html', item=item)

@app.route('/submit-form', methods=['POST'])
def submit_form():
    payload = {
        "catalog_item": request.form['catalog_item'],
        "name": request.form['name'],
        "address": request.form['address'],
        "item_age": int(request.form['item_age']),
        "years_of_insurance": int(request.form['years_of_insurance']),
        "total_price": float(request.form['total_price'])
    }
    response = requests.post(f"{API_URL}/api/apply", json=payload)
    if response.status_code == 200:
        app_id = response.json().get("application_id")
        return redirect(url_for('confirm', app_id=app_id))
    return "Error processing request", 400

@app.route('/confirm/<app_id>')
def confirm(app_id):
    response = requests.get(f"{API_URL}/api/application/{app_id}")
    if response.status_code == 200:
        data = response.json()
        return render_template('confirm.html', app_id=app_id, data=data)
    return "Application expired or not found", 404

@app.route('/final-confirm/<app_id>', methods=['POST'])
def final_confirm(app_id):
    response = requests.post(f"{API_URL}/api/confirm/{app_id}")
    if response.status_code == 200:
        return "<h1>Success! Your insurance policy is confirmed.</h1><a href='/'>Go Home</a>"
    return "Failed to confirm insurance", 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)