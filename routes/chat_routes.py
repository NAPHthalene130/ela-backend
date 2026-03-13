from flask import Blueprint, request, jsonify, Response, stream_with_context
from flask_jwt_extended import jwt_required, get_jwt_identity
from database.dbUtil import getWindowHistory, getChatHistory, creatChatWindow, addChatMessage, deleteUserChatWindow, getCourseList
from database.models import UserChatWindowTable
from util.chat import getChatResponse

chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/courses', methods=['GET'])
@jwt_required()
def get_courses():
    return jsonify({
        'status': 'success',
        'data': getCourseList()
    })

@chat_bp.route('/windows', methods=['GET'])
@jwt_required()
def get_windows():
    current_user_id = get_jwt_identity()
    windows = getWindowHistory(current_user_id)
    return jsonify({
        'status': 'success',
        'data': windows
    })

@chat_bp.route('/history', methods=['GET'])
@jwt_required()
def get_history():
    window_id = request.args.get('windowID')
    if not window_id:
        return jsonify({'status': 'fail', 'msg': 'Missing windowID'}), 400
    
    # 可以在这里校验该 windowID 是否属于当前用户，暂时略过
    history = getChatHistory(window_id)
    return jsonify({
        'status': 'success',
        'data': history
    })

@chat_bp.route('/create', methods=['POST'])
@jwt_required()
def create_window():
    current_user_id = get_jwt_identity()
    window_id = creatChatWindow(current_user_id)
    if window_id:
        return jsonify({
            'status': 'success',
            'data': {'windowID': window_id}
        })
    else:
        return jsonify({'status': 'fail', 'msg': 'Failed to create chat window'}), 500

@chat_bp.route('/send', methods=['POST'])
@jwt_required()
def send_message():
    data = request.get_json()
    window_id = data.get('windowID')
    content = data.get('content')
    is_user_send = data.get('isUserSend', True) # 默认为用户发送

    if not window_id or not content:
        return jsonify({'status': 'fail', 'msg': 'Missing parameters'}), 400

    success = addChatMessage(window_id, content, is_user_send)
    if success:
        return jsonify({'status': 'success', 'msg': 'Message sent'})
    else:
        return jsonify({'status': 'fail', 'msg': 'Failed to save message'}), 500


@chat_bp.route('/stream', methods=['POST'])
@jwt_required()
def chat_stream():
    data = request.get_json()
    window_id = data.get('windowID')
    content = data.get('content')
    course = data.get('course')
    current_user_id = get_jwt_identity()

    if not window_id or not content:
        return jsonify({'status': 'fail', 'msg': 'Missing parameters'}), 400

    # Generator for streaming response
    # Using stream_with_context to keep the request context active for DB operations
    generator = getChatResponse(current_user_id, window_id, content, course)
    
    return Response(stream_with_context(generator), mimetype='text/plain')


@chat_bp.route('/delete-window', methods=['POST'])
@jwt_required()
def delete_window():
    data = request.get_json()
    user_id = data.get('userID')
    window_id = data.get('windowID')
    current_user_id = get_jwt_identity()

    if not user_id or not window_id:
        return jsonify({'status': 'fail', 'msg': 'Missing parameters'}), 400

    if user_id != current_user_id:
        return jsonify({'status': 'fail', 'msg': 'Unauthorized user'}), 403

    target_window = UserChatWindowTable.query.filter_by(id=current_user_id, windowsId=window_id).first()
    if not target_window:
        return jsonify({'status': 'fail', 'msg': 'Window not found'}), 404

    success = deleteUserChatWindow(window_id)
    if success:
        return jsonify({'status': 'success', 'msg': 'Window deleted'})
    return jsonify({'status': 'fail', 'msg': 'Failed to delete window'}), 500
