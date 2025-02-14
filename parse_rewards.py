import re
from datetime import datetime
import pandas as pd

def parse_reward_file(filepath):
    # Extract client_id and worker_id from filename
    filename = filepath.split('/')[-1]
    client_match = re.search(r'client_(?:2_)?UID_(\d+)', filename)
    worker_match = re.search(r'miner[_=](\d+)', filename)
    
    client_id = client_match.group(1) if client_match else None
    worker_id = worker_match.group(1) if worker_match else None
    
    data = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            # Split on ζ or tab
            parts = re.split('[ζ\t]', line.strip())
            if len(parts) >= 2:
                row_num = parts[0]
                # Extract timestamp and reward
                timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}):\d{2}', parts[1])
                reward_match = re.search(r'reward=([0-9.-]+)', parts[1])
                
                if timestamp_match and reward_match:
                    timestamp = datetime.strptime(timestamp_match.group(1), '%Y-%m-%d %H:%M')
                    reward = float(reward_match.group(1))
                    
                    data.append({
                        'client_id': client_id,
                        'worker_id': worker_id,
                        'row_number': row_num,
                        'day': timestamp.day,
                        'hour': timestamp.hour,
                        'minute': timestamp.minute,
                        'reward_size': reward
                    })
    
    return data

def main():
    files = [
        'search_results_client_2_UID_87_Rewarding miner=221.txt',
        'search_results_client_2_UID_87_Rewarding_miner_122.txt',
        'search_results_client_UID_199_Rewarding miner=203.txt',
        'search_results_client_UID_199_Rewarding miner=221.txt',
        'search_results_client_2_UID_87_Rewarding_miner_203.txt',
        'search_results_client_2_UID_87_Rewarding_miner_221.txt'
    ]
    
    all_data = []
    for file in files:
        try:
            print(f"Processing file: {file}")
            all_data.extend(parse_reward_file(file))
        except FileNotFoundError:
            print(f"Warning: File not found: {file}")
            continue
    
    if not all_data:
        print("No data was collected!")
        return
        
    # Convert to DataFrame and sort
    df = pd.DataFrame(all_data)
    df = df.sort_values(['day', 'hour', 'minute'])
    
    # Save to CSV
    df.to_csv('rewards_table.csv', index=False)
    print("Table saved to rewards_table.csv")

if __name__ == "__main__":
    main() 