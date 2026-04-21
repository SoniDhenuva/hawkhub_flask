from flask import Blueprint, jsonify, request

from model.recommendation import (
    get_latest_result_by_username,
    init_db,
    normalize_survey,
    rank_clubs,
    save_result,
)


recommendations_api = Blueprint('recommendations_api', __name__, url_prefix='/api')


def _latest_recommendations_response(username):
    result = get_latest_result_by_username(username)
    if result is None:
        return jsonify({'error': 'No recommendation record found for this username'}), 404
    return jsonify(result)


@recommendations_api.route('/health', methods=['GET'])
def recommendation_health():
    return jsonify({'status': 'ok'})


@recommendations_api.route('/recommendations', methods=['GET', 'POST'])
def create_recommendations():
    if request.method == 'GET':
        username = request.args.get('username', '').strip()
        if not username:
            return jsonify({'error': 'username query parameter is required'}), 400
        return _latest_recommendations_response(username)

    try:
        survey = normalize_survey(request.get_json(silent=True) or {})
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    try:
        init_db()
        ranked = rank_clubs(survey)
        response = save_result(survey['username'], survey, ranked)
        return jsonify(response), 201
    except FileNotFoundError as exc:
        return jsonify({'error': str(exc)}), 500
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@recommendations_api.route('/recommendations/<string:username>', methods=['GET'])
def latest_recommendations(username):
    return _latest_recommendations_response(username)