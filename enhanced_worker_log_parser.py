import re
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from collections import defaultdict
import logging
from dataclasses import asdict, dataclass

# Import the patterns
from log_patterns import REQUEST_PATTERNS, VIDEO_SEARCH_PATTERNS, DOWNLOAD_PATTERNS, ERROR_PATTERNS, ALL_PATTERNS
from log_line import LogLine

@dataclass
class WorkerJob:
    job_id: str  # Will be timestamp or UID
    query: Optional[str] = None
    client_hotkey: Optional[str] = None
    stages: Dict[str, Any] = None
    results: Dict[str, Any] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: str = "unknown"
    incentive: Optional[Dict[str, float]] = None
    query_info: Optional[Dict[str, Any]] = None

class EnhancedWorkerLogParser:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.unrecognized_lines: List[str] = []
        self.current_job: Optional[WorkerJob] = None
        self.jobs: List[WorkerJob] = []
        
    def parse_log(self, log_path: str) -> Dict[str, Any]:
        """Parse the entire log file and return structured data."""
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            current_lines = []
            for line in lines:
                # New job starts with "Incoming request: UID"
                if "Incoming request: UID" in line:
                    if current_lines:
                        self._process_job(current_lines)
                    current_lines = []
                current_lines.append(line)
            
            # Process last job
            if current_lines:
                self._process_job(current_lines)

            return {
                'jobs': [asdict(job) for job in self.jobs],
                'unrecognized_lines': self.unrecognized_lines
            }

        except Exception as e:
            self.logger.error(f"Error parsing log file: {e}")
            raise

    def _process_job(self, lines: List[str]) -> None:
        """Process a single job's lines."""
        # Extract request info first to check if blacklisted
        request_info = self._extract_request_info(lines)
        self.logger.debug(f"Extracted request info: {request_info}")
        
        # Create job with minimal info first
        job = WorkerJob(job_id=str(len(self.jobs)))
        
        # Set client hotkey if available
        if 'client_hotkey' in request_info:
            job.client_hotkey = request_info['client_hotkey']
        else:
            self.logger.warning("No client hotkey found in request info")
        
        # If request was blacklisted, only store minimal information
        if request_info.get('blacklisted', False):
            self.logger.debug("Request was blacklisted")
            job.status = "blacklisted"
            job.stages = {'request': request_info}
            self.jobs.append(job)
            return

        # Continue with full processing for non-blacklisted requests
        self.logger.debug("Processing non-blacklisted request")
        job.stages = {
            'request': request_info,
            'query_processing': self._extract_query_processing(lines),
            'search': self._extract_search_info(lines),
            'download': self._extract_download_info(lines),
            'processing': self._extract_processing_info(lines),
            'filtering': self._extract_filtering_info(lines)
        }
        
        # Extract final results
        job.results = self._extract_results(lines)
        
        # Add incentive extraction
        job.incentive = self._extract_incentive_info(lines)
        self.logger.debug(f"Extracted incentive info: {job.incentive}")
        
        # Update job status based on incentive
        if job.incentive and job.incentive.get('Incentive', 0) > 0:
            job.status = "succeeded"
        else:
            job.status = "failed"
        
        # Add to jobs list
        self.jobs.append(job)

    def _extract_timestamp(self, line: str) -> Optional[str]:
        match = re.search(r'\[34m(.*?)\[39m', line)
        return match.group(1) if match else None

    def _extract_request_info(self, lines: List[str]) -> Dict[str, Any]:
        """Extract information about the request including client hotkey and blacklist status."""
        info = {}
        
        for i, line in enumerate(lines):
            # Look for incoming request line
            if "Incoming request: UID" in line:
                self.logger.debug(f"Found request line: {line.strip()}")
                # Extract hotkey from the request line
                hotkey_match = re.search(r'HK ([^\s]+) -', line)
                if hotkey_match:
                    info['client_hotkey'] = hotkey_match.group(1)
                    self.logger.debug(f"Extracted client hotkey: {info['client_hotkey']}")
                    
                    # Check next few lines for blacklist status
                    for next_line in lines[i:i+5]:
                        if "Blacklisting hotkey" in next_line:
                            info['blacklisted'] = True
                            if "Insufficient stake" in next_line:
                                info['blacklist_reason'] = "Insufficient stake"
                            self.logger.debug("Request is blacklisted")
                            break
                        elif "Not Blacklisting" in next_line:
                            info['blacklisted'] = False
                            self.logger.debug("Request is not blacklisted")
                            break
                else:
                    self.logger.warning("Could not extract hotkey from request line")

            # Only process these if request wasn't blacklisted
            elif not info.get('blacklisted', False):
                if "Received scraping request:" in line:
                    match = re.search(r'(\d+) videos for query \'(.*)\'', line)
                    if match:
                        info['requested_videos'] = int(match.group(1))
                        info['query'] = match.group(2)
                        self.logger.debug(f"Extracted query info: {info['query']}")
                elif "stake=" in line:
                    stake_match = re.search(r'stake=(\d+)', line)
                    if stake_match:
                        info['stake'] = int(stake_match.group(1))
                        self.logger.debug(f"Extracted stake: {info['stake']}")
        
        self.logger.debug(f"Final request info: {info}")
        return info

    def _extract_query_processing(self, lines: List[str]) -> Dict[str, Any]:
        """Extract information about query processing including random topics and augmentation."""
        info = {
            'original_query': None,
            'random_topic': None,
            'augmented_queries': [],
            'augmentation_time': None
        }
        
        for line in lines:
            if "Random topic from list:" in line:
                match = re.search(r'Random topic from list: (.*?)(?:\||$)', line)
                if match:
                    info['random_topic'] = match.group(1).strip()
            elif "Augmented query:" in line:
                match = re.search(r"Augmented query: '([^']+)' -> '([^']+)'", line)
                if match:
                    if not info['original_query']:
                        info['original_query'] = match.group(1)
                    info['augmented_queries'].append(match.group(2))
            elif "Query augmentation took" in line:
                match = re.search(r'took ([\d.]+) s', line)
                if match:
                    info['augmentation_time'] = float(match.group(1))
        
        return info

    def _extract_search_info(self, lines: List[str]) -> Dict[str, Any]:
        info = {'videos_found': 0, 'duplicates_removed': 0}
        for line in lines:
            if "Removed" in line and "duplicate search results" in line:
                match = re.search(r'Removed (\d+) duplicate', line)
                if match:
                    info['duplicates_removed'] = int(match.group(1))
            elif "found" in line and "videos" in line:
                match = re.search(r'found (\d+) videos', line)
                if match:
                    info['videos_found'] = int(match.group(1))
        return info

    def _extract_download_info(self, lines: List[str]) -> Dict[str, Any]:
        info = {'downloaded_videos': 0, 'download_time': None}
        for line in lines:
            if "Downloaded and clipped" in line:
                match = re.search(r'Downloaded and clipped (\d+) videos in ([\d.]+) seconds', line)
                if match:
                    info['downloaded_videos'] = int(match.group(1))
                    info['download_time'] = float(match.group(2))
        return info

    def _extract_processing_info(self, lines: List[str]) -> Dict[str, Any]:
        """Extract information about video processing including load balancer interaction."""
        info = {
            'embedding_time': None,
            'load_balancer': {
                'data_size': None,
                'response_time': None,
                'received_metadata': []
            }
        }
        
        for i, line in enumerate(lines):
            # Track load balancer interaction
            if "Data received from load balancer:" in line:
                data_size_match = re.search(r'Data received from load balancer: (\d+)', line)
                if data_size_match:
                    info['load_balancer']['data_size'] = int(data_size_match.group(1))
                    
                    # Look for the response in the next line
                    if i + 1 < len(lines):
                        response_line = lines[i + 1]
                        if "Received response:" in response_line:
                            # Extract video metadata from response
                            metadata_matches = re.finditer(
                                r'VideoMetadata\(video_id=\'([^\']+)\', description=\'([^\']+)\', '
                                r'views=(\d+), start_time=(\d+), end_time=(\d+)',
                                response_line
                            )
                            for match in metadata_matches:
                                info['load_balancer']['received_metadata'].append({
                                    'video_id': match.group(1),
                                    'description': match.group(2),
                                    'views': int(match.group(3)),
                                    'clip_start': int(match.group(4)),
                                    'clip_end': int(match.group(5))
                                })

            # Track embedding generation time
            elif "Embeddings generation took" in line:
                match = re.search(r'took ([\d.]+) s', line)
                if match:
                    info['embedding_time'] = float(match.group(1))
                
        return info

    def _extract_filtering_info(self, lines: List[str]) -> Dict[str, Any]:
        info = {}
        for line in lines:
            if "unique videos prepared" in line:
                match = re.search(r'(\d+) unique videos prepared', line)
                if match:
                    info['unique_videos'] = int(match.group(1))
        return info

    def _extract_results(self, lines: List[str]) -> Dict[str, Any]:
        """Extract final results including prepared videos and scraping status."""
        results = {
            'final_videos': [],
            'total_time': None,
            'status': None,
            'requested_count': None,
            'delivered_count': None
        }
        
        for line in lines:
            # Extract final video list
            if ". " in line and ": " in line and "[" in line and "]" in line:
                match = re.search(r'\d+\. ([^:]+): (.*?) \[(\d+\.\.\d+)\] (\d+)', line)
                if match:
                    results['final_videos'].append({
                        'video_id': match.group(1),
                        'title': match.group(2),
                        'clip': match.group(3),
                        'views': int(match.group(4))
                    })
            
            # Extract scraping status
            elif "SCRAPING" in line:
                status_match = re.search(r'SCRAPING (SUCCEEDED|FAILED): Scraped (\d+)/(\d+) videos in ([\d.]+)', line)
                if status_match:
                    results['status'] = status_match.group(1)
                    results['delivered_count'] = int(status_match.group(2))
                    results['requested_count'] = int(status_match.group(3))
                    results['total_time'] = float(status_match.group(4))
                
        return results

    def _extract_incentive_info(self, lines: List[str]) -> Dict[str, float]:
        """Extract incentive metrics from log lines."""
        info = {}
        for line in lines:
            if "Emission/day" in line:
                self.logger.debug(f"Found incentive line: {line.strip()}")
                try:
                    # Split by pipe and filter out empty strings
                    metrics = [m.strip() for m in line.split('|') if m.strip()]
                    for metric in metrics:
                        # Only process metrics with colon
                        if ':' in metric:
                            try:
                                key, value = [x.strip() for x in metric.split(':', 1)]
                                # Convert value to float, removing any trailing characters
                                value = float(value.split()[0])
                                info[key] = value
                                self.logger.debug(f"Extracted metric: {key}={value}")
                            except (ValueError, IndexError) as e:
                                self.logger.warning(f"Error parsing metric '{metric}': {e}")
                                continue
                except Exception as e:
                    self.logger.warning(f"Error parsing incentive line: {e}")
                    continue
        
        self.logger.debug(f"Final incentive info: {info}")
        return info

def main():
    logging.basicConfig(level=logging.INFO)
    parser = EnhancedWorkerLogParser()
    results = parser.parse_log('example_worker.txt')
    
    print("\nParsing Results:")
    for job in results['jobs']:
        print(f"\nJob {job['job_id']}:")
        print(f"Status: {job['status']}")
        print("Stages:")
        for stage, info in job['stages'].items():
            print(f"  {stage}: {info}")
        print("Results:")
        print(f"  {job['results']}")

if __name__ == "__main__":
    main() 