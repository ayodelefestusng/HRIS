import json
try:
    print("Reading db_dump.json...")
    with open('db_dump.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Total objects: {len(data)}")
    
    # Priority models
    tenants = [d for d in data if d.get('model') == 'org.tenant']
    users = [d for d in data if d.get('model') == 'users.user']
    
    # Rest of the models
    others = [d for d in data if d.get('model') not in ['org.tenant', 'users.user']]
    
    new_data = tenants + users + others
    
    print(f"Saving reordered_dump.json with {len(new_data)} objects...")
    with open('reordered_dump.json', 'w', encoding='utf-8') as f:
        json.dump(new_data, f)
    
    print("Done.")
        
except Exception as e:
    print(f"Error: {e}")
