from flask import Blueprint, request, jsonify, Response, stream_with_context
from flask_jwt_extended import jwt_required, get_jwt_identity
from database.dbUtil import getWindowHistory, getChatHistory, creatChatWindow, addChatMessage
from util.chat import getChatResponse

chat_bp = Blueprint('chat', __name__)

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
    current_user_id = get_jwt_identity()

    if not window_id or not content:
        return jsonify({'status': 'fail', 'msg': 'Missing parameters'}), 400

    # Generator for streaming response
    # Using stream_with_context to keep the request context active for DB operations
    generator = getChatResponse(current_user_id, window_id, content)
    
    return Response(stream_with_context(generator), mimetype='text/plain')
