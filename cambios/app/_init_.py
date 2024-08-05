from app.routes.epics import epics
from app.routes.tasks import tasks

    app.register_blueprint(epics, url_prefix='/epics')
    app.register_blueprint(tasks, url_prefix='/tasks')
    
def dotenv_to_dict(dotenv_path):
    env_vars = {}
    with open(dotenv_path) as f:
        for line in f:
            key, value = line.split("=")
            env_vars[key] = value
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1) 
                    env_vars[key.strip()] = value.strip()
                else:
                    print(f"Skipping invalid line in .env: {line}")
    return env_vars