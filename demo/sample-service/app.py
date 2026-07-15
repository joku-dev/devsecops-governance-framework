def healthcheck() -> dict:
    return {"status": "ok", "service": "sample-service"}


if __name__ == "__main__":
    print(healthcheck())
