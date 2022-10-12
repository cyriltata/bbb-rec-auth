import os
from dotenv import load_dotenv
from pathlib import Path

class GLAuthConfig:

    env_file = None;

    def __init__(self, env_file='.env'):
        self.env_file = env_file
        
        dotenv_path = Path(self.env_file)
        load_dotenv(dotenv_path=dotenv_path)

    def os(self, var, defalut=None):
        return os.environ.get(var, defalut)

    def env(self, var, defalut=None):
        return os.getenv(var, defalut)

    def get_html(self, file):
        path = Path(__file__).parent.parent.joinpath('forms', file + '.html')

        if path.is_file():
            return str(path.read_text())

        return ""
