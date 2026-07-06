import json
import os
import sqlite3
from datetime import datetime, timezone

import yaml
from flask import current_app


RELATED_TAG_MAP = {
    'math': ['research', 'academic', 'technical'],
    'science': ['research', 'technical', 'academic'],
    'coding': ['technical', 'build', 'research'],
    'design': ['creative', 'create'],
    'english': ['perform', 'research', 'social'],
    'history': ['english', 'research', 'academic'],
    'business': ['lead', 'organize', 'social'],
    'community': ['impact', 'mentor', 'social'],
    'build': ['technical', 'hands-on'],
    'research': ['academic', 'structured'],
    'compete': ['competitive', 'structured'],
    'create': ['creative', 'design'],
    'perform': ['social', 'creative'],
    'organize': ['lead', 'social'],
    'mentor': ['community', 'collaborative'],
    'lead': ['organize', 'social'],
    'technical': ['coding', 'build', 'science', 'research'],
    'collaborative': ['community', 'mentor', 'lead', 'social'],
    'competitive': ['compete', 'fast-paced', 'structured'],
    'creative': ['create', 'design', 'perform'],
    'social': ['community', 'perform', 'mentor'],
    'academic': ['research', 'structured', 'science', 'history', 'english'],
}

GROUP_WEIGHTS = {
    'subjects': 1.4,
    'activities': 1.15,
    'vibes': 1.05,
}


def _database_path():
    return current_app.config['CLUB_RECOMMENDER_DB_PATH']


def _clubs_path():
    return current_app.config['CLUB_RECOMMENDER_CLUBS_PATH']


def _ensure_parent_dir(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _connect():
    db_path = _database_path()
    _ensure_parent_dir(db_path)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with _connect() as connection:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS recommendation_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                submitted_at TEXT NOT NULL,
                grade TEXT NOT NULL,
                subjects_json TEXT NOT NULL,
                activities_json TEXT NOT NULL,
                vibes_json TEXT NOT NULL,
                recommendations_json TEXT NOT NULL
            )
            '''
        )
        connection.commit()


def load_clubs_from_yaml():
    clubs_path = _clubs_path()
    if not os.path.exists(clubs_path):
        raise FileNotFoundError(f'Club YAML file not found: {clubs_path}')

    with open(clubs_path, 'r', encoding='utf-8') as clubs_file:
        payload = yaml.safe_load(clubs_file) or []

    clubs = []
    for club in payload:
        clubs.append({
            'id': str(club['id']).strip(),
            'name': str(club['name']).strip(),
            'summary': str(club.get('summary', '')).strip(),
            'href': str(club.get('href', '')).strip(),
            'image': str(club.get('image', '')).strip(),
            'categories': [str(item).strip() for item in club.get('categories', []) if str(item).strip()],
            'tags': [str(item).strip().lower() for item in club.get('tags', []) if str(item).strip()],
        })
    return clubs


def _normalize_list(values):
    if not isinstance(values, list):
        raise ValueError('Expected a list value')

    normalized = []
    seen = set()
    for value in values:
        cleaned = str(value).strip().lower()
        if cleaned and cleaned not in seen:
            normalized.append(cleaned)
            seen.add(cleaned)
    return normalized


def normalize_survey(payload):
    if not isinstance(payload, dict):
        raise ValueError('Request body must be a JSON object')

    username = str(payload.get('username', '')).strip()
    grade = str(payload.get('grade', '')).strip()
    if not username:
        raise ValueError('username is required')
    if not grade:
        raise ValueError('grade is required')

    try:
        subjects = _normalize_list(payload.get('subjects', []))
        activities = _normalize_list(payload.get('activities', []))
        vibes = _normalize_list(payload.get('vibes', []))
    except ValueError:
        raise ValueError('subjects, activities, and vibes must each be lists')

    if not subjects:
        raise ValueError('subjects must contain at least one selection')
    if not activities:
        raise ValueError('activities must contain at least one selection')
    if not vibes:
        raise ValueError('vibes must contain at least one selection')

    return {
        'username': username,
        'grade': grade,
        'subjects': subjects,
        'activities': activities,
        'vibes': vibes,
    }


def score_club(club, survey):
    tags = set(club['tags'])
    score = 0.0
    matched_tags = []
    matched_tag_set = set()
    matched_groups = 0

    for group_name, selected_items in (
        ('subjects', survey['subjects']),
        ('activities', survey['activities']),
        ('vibes', survey['vibes']),
    ):
        group_weight = GROUP_WEIGHTS[group_name]
        group_matched = False

        for selected_item in selected_items:
            if selected_item in tags:
                score += group_weight
                group_matched = True
                if selected_item not in matched_tag_set:
                    matched_tag_set.add(selected_item)
                    matched_tags.append(selected_item)

            affinity_matches = [tag for tag in RELATED_TAG_MAP.get(selected_item, []) if tag in tags]
            if affinity_matches:
                score += min(group_weight * 0.7, 0.35 + len(affinity_matches) * 0.16)
                group_matched = True
                for affinity_tag in affinity_matches:
                    if affinity_tag not in matched_tag_set:
                        matched_tag_set.add(affinity_tag)
                        matched_tags.append(affinity_tag)

        if group_matched:
            matched_groups += 1

    score += min(len(matched_tags) * 0.18, 0.72)
    if matched_groups == 3:
        score += 0.55
    elif matched_groups == 2:
        score += 0.25

    max_score = 0.0
    for group_name, selected_items in (
        ('subjects', survey['subjects']),
        ('activities', survey['activities']),
        ('vibes', survey['vibes']),
    ):
        group_weight = GROUP_WEIGHTS[group_name]
        max_score += len(selected_items) * (group_weight + group_weight * 0.7)
    max_score += min((len(survey['subjects']) + len(survey['activities']) + len(survey['vibes'])) * 0.18, 0.72)
    max_score += 0.55

    if max_score <= 0:
        percentage = 35
    else:
        percentage = round((score / max_score) * 100)
        percentage = max(35, min(98, percentage))

    return {
        'club_id': club['id'],
        'club_name': club['name'],
        'match_percentage': int(percentage),
        'summary': club['summary'],
        'href': club['href'],
        'image_filename': club.get('image', ''),
        'matched_tags': matched_tags,
    }


def rank_clubs(survey):
    clubs = load_clubs_from_yaml()
    ranked = []
    for club in clubs:
        ranked.append(score_club(club, survey))

    ranked.sort(
        key=lambda item: (item['match_percentage'], len(item['matched_tags']), item['club_name']),
        reverse=True,
    )

    results = []
    for index, item in enumerate(ranked, start=1):
        results.append({
            'rank': index,
            **item,
        })
    return results


def _submitted_at_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def save_result(username, survey, recommendations):
    init_db()
    submitted_at = _submitted_at_iso()
    with _connect() as connection:
        connection.execute(
            '''
            INSERT INTO recommendation_runs (
                username,
                submitted_at,
                grade,
                subjects_json,
                activities_json,
                vibes_json,
                recommendations_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                username,
                submitted_at,
                survey['grade'],
                json.dumps(survey['subjects']),
                json.dumps(survey['activities']),
                json.dumps(survey['vibes']),
                json.dumps(recommendations),
            ),
        )
        connection.commit()

    return {
        'username': username,
        'submitted_at': submitted_at,
        'survey': {
            'grade': survey['grade'],
            'subjects': survey['subjects'],
            'activities': survey['activities'],
            'vibes': survey['vibes'],
        },
        'recommendations': recommendations,
    }


def get_latest_result_by_username(username):
    init_db()
    with _connect() as connection:
        row = connection.execute(
            '''
            SELECT username, submitted_at, grade, subjects_json, activities_json, vibes_json, recommendations_json
            FROM recommendation_runs
            WHERE username = ?
            ORDER BY id DESC
            LIMIT 1
            ''',
            (username,),
        ).fetchone()

    if row is None:
        return None

    return {
        'username': row['username'],
        'submitted_at': row['submitted_at'],
        'survey': {
            'grade': row['grade'],
            'subjects': json.loads(row['subjects_json']),
            'activities': json.loads(row['activities_json']),
            'vibes': json.loads(row['vibes_json']),
        },
        'recommendations': json.loads(row['recommendations_json']),
    }