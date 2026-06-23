from ninja import Schema


class LoginSchema(Schema):
    """
    Schema that contains the login information.
    """

    username: str
    password: str


class RegisterSchema(Schema):
    """
    Schema with the data needed to create a new account.
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


class RegisterResultSchema(Schema):
    """
    Outcome of a registration request. Accounts are gated, so registering does
    not sign the user in; it queues the account for admin approval.
    """

    status: str
    message: str
