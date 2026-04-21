import json
import os

from flask import Blueprint, current_app, jsonify


club_finder_api = Blueprint('club_finder_api', __name__, url_prefix='/api/club-finder')


def load_club_finder_layout():
    layout_path = current_app.config['CLUB_FINDER_LAYOUT_PATH']
    if not os.path.exists(layout_path):
        raise FileNotFoundError(f'Club finder layout file not found: {layout_path}')

    with open(layout_path, 'r', encoding='utf-8') as layout_file:
        payload = json.load(layout_file)

    payload['step_count'] = len(payload.get('steps', []))
    return payload


@club_finder_api.route('/layout', methods=['GET'])
def club_finder_layout():
    try:
        return jsonify(load_club_finder_layout())
    except FileNotFoundError as exc:
        return jsonify({'error': str(exc)}), 404
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500