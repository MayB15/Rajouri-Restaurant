"""
Updated validate_queue.py using common utilities
"""

import sys
import os
import unreal 

# Add the common directory to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
common_dir = os.path.join(script_dir, 'lib')
if common_dir not in sys.path:
    sys.path.append(common_dir)

# Import from common module
from render_queue_validation import validate_movie_render_queue

if __name__ == "__main__":
    
    unreal.log(validate_movie_render_queue())