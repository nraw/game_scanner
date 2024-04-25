users = [1901217395, 6200147668]


def check_is_user(user_id):
    if user_id in users:
        return True, 100
    return False, 0
