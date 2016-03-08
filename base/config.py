import os

# Define proxy
proxy = os.environ.get('OOI_PROXY', None)

# Define cookie secret key
secret_key = os.environ.get('OOI_SECRET_KEY', 'You Must Set A Secret Key!').encode()

# Define project structure
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
template_dir = os.path.join(base_dir, 'templates')
static_dir = os.path.join(base_dir, 'static')
kcs_dir = os.path.join(base_dir, '_kcs')
