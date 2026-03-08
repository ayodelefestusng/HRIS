import json
import os

def split_json(filename, chunk_size=1000):
    try:
        print(f"Reading {filename}...")
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        total = len(data)
        print(f"Total objects: {total}")
        
        if not os.path.exists('chunks'):
            os.makedirs('chunks')
        
        for i in range(0, total, chunk_size):
            chunk = data[i:i+chunk_size]
            chunk_filename = f"chunks/chunk_{i//chunk_size:03d}.json"
            print(f"Saving {chunk_filename}...")
            with open(chunk_filename, 'w', encoding='utf-8') as f:
                json.dump(chunk, f)
        
        print("Done.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    split_json('reordered_dump.json')
