import os
import subprocess
import time

def load_chunks():
    chunk_dir = 'chunks'
    files = sorted([f for f in os.listdir(chunk_dir) if f.endswith('.json')])
    
    for filename in files:
        filepath = os.path.join(chunk_dir, filename)
        print(f"Loading {filepath}...")
        
        start_time = time.time()
        # Using subprocess to run manage.py loaddata
        result = subprocess.run(['python', 'manage.py', 'loaddata', filepath], capture_output=True, text=True)
        
        duration = time.time() - start_time
        
        if result.returncode == 0:
            print(f"Successfully loaded {filepath} in {duration:.2f}s")
            print(result.stdout.strip())
        else:
            print(f"FAILED to load {filepath} in {duration:.2f}s")
            print(result.stderr)
            # Stop on failure
            break

if __name__ == "__main__":
    load_chunks()
