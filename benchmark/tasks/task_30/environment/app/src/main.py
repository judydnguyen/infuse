from src.parser import load_job_config


def healthcheck() -> str:
    cfg = load_job_config("data/job.yaml")
    return "ok" if cfg.get("job_name") == "nightly-index" else "error"


if __name__ == "__main__":
    print(healthcheck())
