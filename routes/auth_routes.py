from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from auth.AuthDataBaseUtil import login, register, requireEmailCode
from database.models import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login_route():
    data = request.get_json()
    user_id = data.get('id')
    password = data.get('password')

    if not user_id or not password:
        return jsonify({'status': 'fail', 'msg': 'Missing id or password'}), 400

    user = login(user_id, password)
    if user:
        access_token = create_access_token(identity=user.id)
        return jsonify({
            'status': 'success',
            'msg': 'Login successful',
            'user': {'id': user.id, 'email': user.email},
            'token': access_token
        })
    else:
        return jsonify({'status': 'fail', 'msg': 'Invalid id or password'}), 401

@auth_bp.route('/register', methods=['POST'])
def register_route():
    data = request.get_json()
    user_id = data.get('id')
    password = data.get('password')
    email = data.get('email')
    email_code = data.get('emailCode')

    if not all([user_id, password, email, email_code]):
        return jsonify({'status': 'fail', 'msg': 'Missing required fields'}), 400

    success, message = register(user_id, password, email, email_code)
    if success:
        return jsonify({'status': 'success', 'msg': message})
    else:
        return jsonify({'status': 'fail', 'msg': message}), 400

@auth_bp.route('/send-code', methods=['POST'])
def send_code_route():
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'status': 'fail', 'msg': 'Missing email'}), 400

    success, message = requireEmailCode(email)
    if success:
        return jsonify({'status': 'success', 'msg': message})
    else:
        return jsonify({'status': 'fail', 'msg': message}), 500

@auth_bp.route('/check-id', methods=['GET'])
def check_id_route():
    user_id = request.args.get('id')
    if not user_id:
        return jsonify({'status': 'fail', 'msg': 'Missing id parameter'}), 400
    
    user = User.query.filter_by(id=user_id).first()
    if user:
        return jsonify({'status': 'success', 'exists': True, 'msg': 'User ID exists'})
    else:
        return jsonify({'status': 'success', 'exists': False, 'msg': 'User ID available'})
