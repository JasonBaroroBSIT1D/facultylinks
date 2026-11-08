import pytest

from app import create_app


@pytest.fixture
def app():
    app = create_app()
    app.config.update({"TESTING": True})
    return app


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app
