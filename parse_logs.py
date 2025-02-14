import re
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional
import logging
import os

@dataclass
class Task:
    timestamp: datetime
    query: str
    reward: Optional[float] = None
    worker_response: Optional[str] = None

def parse_client_log(client_log_path: str, worker_id: int) -> List[Task]:
    """Parse client log to find tasks sent to specific worker and their rewards."""
    tasks = []
    current_task = None
    
    logger.info(f"Worker ID to look for: {worker_id}")
    
    with open(client_log_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            # Print first few lines to debug
            if line_num <= 5:
                logger.debug(f"Line {line_num}: {line.strip()}")
            
            # Parse timestamp - updated pattern to match actual format
            timestamp_match = re.search(r'\[34m(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\[39m', line)
            if timestamp_match:
                logger.debug(f"Found timestamp: {timestamp_match.group(1)}")
                timestamp = datetime.strptime(timestamp_match.group(1), '%Y-%m-%d %H:%M:%S.%f')
            
                # Look for queries sent to miners - print the line if it contains "Sending query"
                if "Sending query" in line:
                    logger.debug(f"Found query line: {line.strip()}")
                
                query_match = re.search(r"Sending query '([^']+)' to miners tensor\((\[[\d\s,]+\])", line)
                if query_match:
                    miners = eval(query_match.group(2))
                    logger.debug(f"Found query with miners: {miners}")
                    if worker_id in miners:
                        current_task = Task(
                            timestamp=timestamp,
                            query=query_match.group(1)
                        )
                        tasks.append(current_task)
                        logger.debug(f"Added task with query: {query_match.group(1)}")
            
            # Look for rewards
            reward_match = re.search(f"Rewarding miner={worker_id} with reward=([0-9.]+)", line)
            if reward_match and current_task:
                current_task.reward = float(reward_match.group(1))
                logger.debug(f"Added reward: {reward_match.group(1)}")
    
    logger.info(f"Total tasks found: {len(tasks)}")
    if len(tasks) > 0:
        logger.info(f"Sample task: {tasks[0]}")
    
    return tasks

def parse_worker_log(worker_log_path: str, client_id: int) -> List[Task]:
    """Parse worker log to find responses to specific client."""
    tasks = []
    
    with open(worker_log_path, 'r', encoding='utf-8') as f:
        content = f.read()
        # Print first 200 chars to debug
        logger.debug(f"First 200 chars of worker log:\n{content[:200]}")
        
        # Print all occurrences of "Incoming request: UID"
        all_requests = re.findall(r'Incoming request: UID \d+', content)
        logger.debug(f"All incoming requests found: {all_requests}")
        
        # Find all sections starting with "Incoming request: UID" for the specific client
        pattern = r'Incoming request: UID ' + str(client_id) + r'\s*\n(.*?)(?=Incoming request: UID|\Z)'
        logger.debug(f"Using pattern: {pattern}")
        
        sections = re.finditer(pattern, content, re.DOTALL)
        
        for section in sections:
            response = section.group(1).strip()
            logger.debug(f"Found response section: {response[:100]}...")  # First 100 chars
            tasks.append(Task(
                timestamp=None,
                query="",
                worker_response=response
            ))
    
    logger.info(f"Found {len(tasks)} responses for client {client_id}")
    return tasks

def match_tasks(client_tasks: List[Task], worker_tasks: List[Task]) -> List[Task]:
    """Match client tasks with worker responses in chronological order."""
    matched_tasks = []
    
    # Assuming responses are in same chronological order as requests
    for client_task, worker_task in zip(client_tasks, worker_tasks):
        matched_task = Task(
            timestamp=client_task.timestamp,
            query=client_task.query,
            reward=client_task.reward,
            worker_response=worker_task.worker_response
        )
        matched_tasks.append(matched_task)
            
    return matched_tasks

def write_matched_tasks(tasks: List[Task], output_path: str, client_id: int, worker_id: int):
    """Write matched tasks to output file."""
    with open(output_path, 'w') as f:
        f.write(f"=== Matched Tasks Between Client {client_id} and Worker {worker_id} ===\n\n")
        
        for i, task in enumerate(tasks, 1):
            f.write(f"Task {i}\n")
            f.write(f"Timestamp: {task.timestamp}\n")
            f.write(f"Query: {task.query}\n")
            if task.reward is not None:
                f.write(f"Reward: {task.reward}\n")
            if task.worker_response:
                f.write("Worker Response:\n")
                f.write(task.worker_response)
            f.write("\n" + "="*50 + "\n\n")

def main():
    try:
        # Check if files exist
        client_log_path = 'client_log/client_UID_199.log'
        worker_log_path = 'worker_rtf/UID_122.rtf'
        
        client_id = 199  # Extracted from filename
        worker_id = 122 # Extracted from filename
        
        for path in [client_log_path, worker_log_path]:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Could not find file: {path}")
        
        logger.info(f"Parsing client log: {client_log_path}")
        client_tasks = parse_client_log(client_log_path, worker_id)
        logger.info(f"Found {len(client_tasks)} client tasks")
        
        logger.info(f"Parsing worker log: {worker_log_path}")
        worker_tasks = parse_worker_log(worker_log_path, client_id)
        logger.info(f"Found {len(worker_tasks)} worker tasks")
        
        # Match tasks
        matched_tasks = match_tasks(client_tasks, worker_tasks)
        logger.info(f"Matched {len(matched_tasks)} tasks")
        
        # Write output
        write_matched_tasks(matched_tasks, 'matched_tasks.txt', client_id, worker_id)
        logger.info("Results written to matched_tasks.txt")
        
    except Exception as e:
        logger.error(f"Error processing logs: {str(e)}")
        raise

if __name__ == "__main__":
    # Set up logging with debug level
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    main() 