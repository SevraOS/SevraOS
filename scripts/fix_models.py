import os
import glob
import re

models_dir = 'backend/database/models'
for filepath in glob.glob(os.path.join(models_dir, '*.py')):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Replace 'ix_{name}_sync_status' with 'ix_{name}_sync_created' in Index definitions
    new_content = re.sub(r'Index\(\"ix_([a-zA-Z0-9_]+)_sync_status\", \"sync_status\", \"created_at\"\)', r'Index("ix_\1_sync_created", "sync_status", "created_at")', content)
    
    if new_content != content:
        with open(filepath, 'w') as f:
            f.write(new_content)
        print(f'Fixed {filepath}')
