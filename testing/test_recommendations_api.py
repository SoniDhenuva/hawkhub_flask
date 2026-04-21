import os
import tempfile
import unittest

from main import app


TEST_CLUBS_YAML = '''
- id: optix
  name: FRC TEAM OPTIX 3749
  summary: Build robots, code systems, and compete in high-intensity engineering events.
  href: /search
  image: clubs/optix.png
  categories: [STEM, Competition, All Clubs]
  tags: [coding, science, build, compete, hands-on, fast-paced, structured]
- id: girls-in-cs
  name: Girls In CS
  summary: Learn coding collaboratively and build confidence through technical projects.
  href: /search
  image: clubs/girls_in_cs.png
  categories: [STEM, All Clubs]
  tags: [coding, math, science, build, create, social, impact]
- id: interact
  name: Interact Club
  summary: Coordinate volunteering and local service events with measurable impact.
  href: /search
  image: clubs/interact.png
  categories: [Charity/Volunteer, All Clubs]
  tags: [community, impact, organize, lead, social, hands-on]
'''


class RecommendationsApiTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, 'club_recommendations.db')
        self.clubs_path = os.path.join(self.temp_dir.name, 'school_clubs.yml')
        with open(self.clubs_path, 'w', encoding='utf-8') as clubs_file:
            clubs_file.write(TEST_CLUBS_YAML)

        app.config['TESTING'] = True
        app.config['CLUB_RECOMMENDER_DB_PATH'] = self.db_path
        app.config['CLUB_RECOMMENDER_CLUBS_PATH'] = self.clubs_path
        self.client = app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_health_endpoint(self):
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': 'ok'})

    def test_post_and_get_recommendations(self):
        payload = {
            'username': 'jane_doe',
            'grade': '11',
            'subjects': ['coding', 'math'],
            'activities': ['build', 'compete'],
            'vibes': ['technical', 'competitive'],
        }
        post_response = self.client.post('/api/recommendations', json=payload)
        self.assertEqual(post_response.status_code, 201)
        post_json = post_response.get_json()
        self.assertEqual(post_json['username'], 'jane_doe')
        self.assertEqual(post_json['recommendations'][0]['club_id'], 'optix')
        self.assertIsInstance(post_json['recommendations'][0]['match_percentage'], int)

        get_response = self.client.get('/api/recommendations/jane_doe')
        self.assertEqual(get_response.status_code, 200)
        get_json = get_response.get_json()
        self.assertEqual(get_json['username'], 'jane_doe')
        self.assertEqual(get_json['recommendations'][0]['club_id'], post_json['recommendations'][0]['club_id'])

        query_response = self.client.get('/api/recommendations?username=jane_doe')
        self.assertEqual(query_response.status_code, 200)
        query_json = query_response.get_json()
        self.assertEqual(query_json['username'], 'jane_doe')
        self.assertEqual(query_json['recommendations'][0]['club_id'], post_json['recommendations'][0]['club_id'])

    def test_missing_user_returns_404(self):
        response = self.client.get('/api/recommendations/missing_user')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {'error': 'No recommendation record found for this username'})

    def test_missing_fields_return_400(self):
        response = self.client.post('/api/recommendations', json={'username': 'jane_doe'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.get_json())

    def test_get_recommendations_requires_username_query_parameter(self):
        response = self.client.get('/api/recommendations')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'error': 'username query parameter is required'})


if __name__ == '__main__':
    unittest.main()