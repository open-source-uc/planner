class Consts:
    class Frontend:
        login_fail = "http://localhost:3000/login_fail"
        login_success = "http://localhost:3000"

    class Jwt:
        secret = "4ff103da3c3ec1792b7cd05db9fc52877103a3c699d407a50ef24ba598aaf467"
        algorithm = "HS256"

    default_login_expire = 60
