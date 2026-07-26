
import os


deploy_env = os.environ.get("DEPLOY_ENV", "").strip()
if not deploy_env:
    raise RuntimeError("DEPLOY_ENV is required")
if deploy_env not in {"staging", "production"}:
    raise RuntimeError("DEPLOY_ENV must be staging or production")
