import requests


def get(url,  headers=None, **kwargs):
    args = kwargs.items()
    if len(args) > 0:
        url += f"?{'&'.join([f'{key}={value}' for key, value in args])}"

    result = requests.get(url, headers=headers, allow_redirects=True)
    if result.status_code == 200:
        return result.text

    return None


def post(url, body, headers=None, **kwargs):
    args = kwargs.items()
    if len(args) > 0:
        url += f"?{'&'.join([f'{key}={value}' for key, value in args])}"
    result = requests.post(url, data=body, headers=headers)
    if result.status_code == 200:
        return result.text

    return None

def make_url(base_url, path):
    return f"{base_url}/{path}"