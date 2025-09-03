
# app.py

from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/calculate', methods=['GET'])
def calculate():
    lat1 = float(request.args.get('lat1'))
    lon1 = float(request.args.get('lon1'))
    lat2 = float(request.args.get('lat2'))
    lon2 = float(request.args.get('lon2'))
    distance = calculate_distance(lat1, lon1, lat2, lon2)
    return jsonify({'distance': distance})

# Removed any references to elevation in the API responses.
