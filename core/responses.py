from flask import jsonify


def success_response(data=None, msg: str = "success", status_code: int = 200):
    payload = {"status": "success", "msg": msg}
    if data is not None:
        payload["data"] = data
    return jsonify(payload), status_code


def fail_response(msg: str, status_code: int = 400):
    return jsonify({"status": "fail", "msg": msg}), status_code
