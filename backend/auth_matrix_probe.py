import json
import os

os.environ['PROTREBOT_WEB_REQUIRE_AUTH'] = 'true'
os.environ['PROTREBOT_WEB_ACCESS_TOKEN'] = 'owner-preview-token-1234567890'

from fastapi.testclient import TestClient
from app.main import app
from app.commercial_core import issue_token

with TestClient(app) as client:
    secret = app.state.v22_commercial['secret']
    owner_jwt = issue_token('owner-1', 'OWNER', secret, ttl_seconds=3600)
    customer_jwt = issue_token('customer-1', 'CUSTOMER', secret, ttl_seconds=3600)

    state = app.state.v22_commercial['state']
    state['users'] = [
        {'id': 'owner-1', 'email': 'owner@example.com', 'display_name': 'Owner', 'role': 'OWNER', 'active': True, 'auth_version': 1},
        {'id': 'customer-1', 'email': 'customer@example.com', 'display_name': 'Customer', 'role': 'CUSTOMER', 'active': True, 'auth_version': 1},
    ]
    state['owner_user_id'] = 'owner-1'

    cases = [
        ('/api/web/access/check', {'X-ProTreBot-Owner': 'owner-preview-token-1234567890'}, 'valid_owner_header'),
        ('/api/web/access/check', {'X-ProTreBot-Owner': 'wrong-token'}, 'wrong_owner_header'),
        ('/api/web/access/check', {'Authorization': 'Bearer customer-token'}, 'customer_bearer_only'),
        ('/api/v22/session', {'Authorization': f'Bearer {customer_jwt}'}, 'v22_customer_jwt_ok'),
        ('/api/v22/session', {}, 'v22_without_auth'),
        ('/api/v22/admin/overview', {'Authorization': f'Bearer {customer_jwt}'}, 'v22_customer_admin_forbidden'),
        ('/api/v22/admin/overview', {'Authorization': f'Bearer {owner_jwt}'}, 'v22_owner_admin_ok'),
        ('/api/v25/status', {'Authorization': f'Bearer {customer_jwt}'}, 'v25_customer_jwt_forbidden'),
        ('/api/v25/status', {'Authorization': f'Bearer {owner_jwt}'}, 'v25_owner_jwt_ok'),
    ]

    results = []
    for path, headers, label in cases:
        resp = client.get(path, headers=headers)
        results.append({
            'label': label,
            'path': path,
            'status': resp.status_code,
            'auth_header': headers,
            'body_prefix': resp.text[:220],
        })

    print(json.dumps(results, ensure_ascii=False, indent=2))
