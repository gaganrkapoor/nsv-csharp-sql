import os
import sys

# Add the .python_packages directory to the Python path
function_app_root = os.path.dirname(os.path.abspath(__file__))
python_packages_path = os.path.join(function_app_root, '.python_packages', 'lib', 'site-packages')
if python_packages_path not in sys.path:
    sys.path.insert(0, python_packages_path)

from dotenv import load_dotenv

def load_env():
    load_dotenv()
    # Optionally, print or log loaded envs for debugging
    # print(os.environ)
