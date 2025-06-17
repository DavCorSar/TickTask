from ninja import Schema


class LoginSchema(Schema):
    """
    Schema that contains the login information.
    """

    username: str
    password: str


class TokenSchema(Schema):
    """
    Schema that contains the information of
    the token to keep the session open.
    """

    access: str
    refresh: str
