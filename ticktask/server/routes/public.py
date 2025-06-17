from ninja import Router

public_router = Router()


@public_router.get("/hello", tags=["Public"])
def hello_world(request):
    """
    Definition of a simple public route
    """
    return {"message": "Hello! From backend"}
