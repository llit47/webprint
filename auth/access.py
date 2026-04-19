def get_access_identity(request):
    return {
        "email": request.headers.get("Cf-Access-Authenticated-User-Email"),
        "jwt": request.headers.get("Cf-Access-Jwt-Assertion"),
    }
