from app import healthcheck


def test_healthcheck():
    assert healthcheck() == "ok"
