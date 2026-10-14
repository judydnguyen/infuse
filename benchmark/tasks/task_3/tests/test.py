import sys

def main():
    try:
        import numpy as np
        import requests
    except Exception as e:
        print(f"IMPORT_ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Basic sanity checks (prevents fake installs)
    a = np.array([1, 2, 3])
    if a.sum() != 6:
        print("NUMPY_BROKEN", file=sys.stderr)
        sys.exit(1)

    r = requests.models.Response()
    if r.status_code is None:
        print("REQUESTS_BROKEN", file=sys.stderr)
        sys.exit(1)

    print("OK")

if __name__ == "__main__":
    main()