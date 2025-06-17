from ninja import Router
from ninja_jwt.authentication import JWTAuth


private_router = Router()


@private_router.get("/hello", tags=["Private"], auth=JWTAuth())
def protected_route(request):
    """
    Definition of a private route
    """
    return {"message": f"Welcome {request.auth}"}
