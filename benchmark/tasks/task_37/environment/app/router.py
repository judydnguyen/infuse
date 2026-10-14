def build_redirect(next_path: str) -> str:
    if not next_path:
        return "/"
    return next_path


def redirect_response(next_path: str) -> dict:
    return {"location": build_redirect(next_path), "status_code": 302}
