import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from patreon_tier_alerter.src import alerter

class DummyMessages:
    def __init__(self, recorded):
        self.recorded = recorded
    def create(self, body, from_, to):
        self.recorded['body'] = body
        self.recorded['from'] = from_
        self.recorded['to'] = to
        class Resp:
            sid = 'SID123'
        return Resp()

class DummyClient:
    def __init__(self, sid, token, recorded):
        recorded['sid'] = sid
        recorded['token'] = token
        self.messages = DummyMessages(recorded)


def test_send_alerts_twilio(monkeypatch):
    recorded = {}
    def client_factory(sid, token):
        return DummyClient(sid, token, recorded)
    monkeypatch.setattr(alerter, 'Client', client_factory)

    alerts = [{
        'tier_name': 'T',
        'creator_name': 'C',
        'url': 'u'
    }]
    cfg = {
        'provider': 'twilio',
        'twilio_account_sid': 'sid',
        'twilio_auth_token': 'token',
        'twilio_from_number': '+111',
        'recipient_phone_number': '+222'
    }

    alerter.send_alerts(alerts, cfg)

    assert recorded['from'] == '+111'
    assert recorded['to'] == '+222'
    assert recorded['body'].startswith('Patreon Alert')
