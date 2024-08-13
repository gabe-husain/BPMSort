class Config(object):
    DEBUG = False
    TESTING = False
    SECRET_KEY ="aduhiIYGYFE868gYYgugyjg795GGguy"


class ProductionConfig(Config):
    SECRET_KEY ="aduhiIYGYFE868gYYgugyjg795GGguy"

    pass

class DevelopmentConfig(Config):
    SECRET_KEY ="aduhiIYGYFE868gYYgugyjg795GGguy"
    DEBUG = True

class TestingConfig(Config):
    SECRET_KEY ="aduhiIYGYFE868gYYgugyjg795GGguy"
    TESTING = True
