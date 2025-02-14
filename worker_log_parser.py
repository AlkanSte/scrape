import re
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
import logging

@dataclass
class RequestMetadata:
    timestamp: str
    uid: str
    hotkey: str
    timeout: float
    stake: float
    is_blacklisted: bool
    blacklist_reason: Optional[str] = None

@dataclass
class QueryInfo:
    original_query: str
    augmented_queries: List[str]
    augmentation_time: Optional[float] = None

@dataclass
class VideoSearchResults:
    total_videos_found: int
    unique_videos: int
    duplicates_removed: int
    search_time: float
    videos: List[Dict[str, Any]]

@dataclass
class DownloadStats:
    concurrent_downloads: int
    proxies_used: List[str]
    download_times: Dict[str, float]
    average_download_time: float

@dataclass
class WorkRequest:
    # Basic request info
    request_metadata: RequestMetadata
    
    # Query processing (if not blacklisted)
    query_info: Optional[QueryInfo] = None
    
    # Video search results (if not blacklisted)
    video_search: Optional[VideoSearchResults] = None
    
    # Download information (if not blacklisted)
    download_stats: Optional[DownloadStats] = None
    
    # Final status
    final_status: str = "OMITTED"
    error_message: Optional[str] = None

class WorkerLogParser:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def parse_timestamp(self, line: str) -> Optional[str]:
        match = re.search(r'\[34m(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})', line)
        return match.group(1) if match else None

    def parse_request_metadata(self, lines: List[str]) -> Optional[RequestMetadata]:
        for line in lines:
            if "Incoming request: UID" in line:
                match = re.search(r'UID (\d+) - HK ([^\s]+) - timeout (\d+\.\d+) s - stake (\d+)', line)
                if match:
                    uid, hotkey, timeout, stake = match.groups()
                    
                    # Look for blacklist info in next few lines
                    is_blacklisted = False
                    blacklist_reason = None
                    for next_line in lines[lines.index(line):lines.index(line)+5]:
                        if "Blacklisting hotkey" in next_line:
                            is_blacklisted = True
                            reason_match = re.search(r'Blacklisted: True, (.+)', next_line)
                            if reason_match:
                                blacklist_reason = reason_match.group(1)
                    
                    return RequestMetadata(
                        timestamp=self.parse_timestamp(line),
                        uid=uid,
                        hotkey=hotkey,
                        timeout=float(timeout),
                        stake=float(stake),
                        is_blacklisted=is_blacklisted,
                        blacklist_reason=blacklist_reason
                    )
        return None

    def parse_query_info(self, lines: List[str]) -> Optional[QueryInfo]:
        original_query = None
        augmented_queries = []
        augmentation_time = None
        
        for line in lines:
            if "Received scraping request:" in line:
                match = re.search(r'query \'([^\']+)\'', line)
                if match:
                    original_query = match.group(1)
            elif "Augmented query:" in line:
                match = re.search(r'-> \'([^\']+)\'', line)
                if match:
                    augmented_queries.append(match.group(1))
            elif "Query augmentation took" in line:
                match = re.search(r'took (\d+\.\d+)', line)
                if match:
                    augmentation_time = float(match.group(1))
        
        if original_query:
            return QueryInfo(
                original_query=original_query,
                augmented_queries=augmented_queries,
                augmentation_time=augmentation_time
            )
        return None

    def parse_video_search(self, lines: List[str]) -> Optional[VideoSearchResults]:
        videos_found = 0
        unique_videos = 0
        duplicates = 0
        search_time = None
        videos = []
        
        for line in lines:
            if "duplicate search results" in line:
                match = re.search(r'Removed (\d+)', line)
                if match:
                    duplicates += int(match.group(1))
            elif "Video search took" in line:
                match = re.search(r'took (\d+\.\d+)', line)
                if match:
                    search_time = float(match.group(1))
            elif "video_id=" in line:
                video_match = re.search(r"video_id='([^']+)'.*title='([^']+)'.*views=(\d+)", line)
                if video_match:
                    videos.append({
                        'video_id': video_match.group(1),
                        'title': video_match.group(2),
                        'views': int(video_match.group(3))
                    })
        
        if videos:
            return VideoSearchResults(
                total_videos_found=len(videos),
                unique_videos=len(videos) - duplicates,
                duplicates_removed=duplicates,
                search_time=search_time or 0.0,
                videos=videos
            )
        return None

    def parse_download_stats(self, lines: List[str]) -> Optional[DownloadStats]:
        proxies = []
        download_times = {}
        avg_time = None
        
        for line in lines:
            if "Using proxy:" in line:
                match = re.search(r'proxy: ([^\s]+)', line)
                if match:
                    proxies.append(match.group(1))
            elif "Average download time:" in line:
                match = re.search(r'time: (\d+\.\d+)', line)
                if match:
                    avg_time = float(match.group(1))
            elif "Downloaded video" in line and "Proxy used:" in line:
                match = re.search(r'video ([^\s]+).*Proxy used: ([^\s]+) \((\d+\.\d+)\)', line)
                if match:
                    video_id, proxy, time = match.groups()
                    download_times[video_id] = float(time)
        
        if proxies:
            return DownloadStats(
                concurrent_downloads=len(proxies),
                proxies_used=proxies,
                download_times=download_times,
                average_download_time=avg_time or 0.0
            )
        return None

    def parse_log(self, log_path: str) -> List[Dict[str, Any]]:
        requests = []
        current_lines = []
        
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # Group lines by request
        for line in lines:
            if "Incoming request: UID" in line and current_lines:
                # Process previous request
                request = self.process_request(current_lines)
                if request:
                    requests.append(asdict(request))
                current_lines = []
            current_lines.append(line)
            
        # Process last request
        if current_lines:
            request = self.process_request(current_lines)
            if request:
                requests.append(asdict(request))
                
        return requests

    def process_request(self, lines: List[str]) -> Optional[WorkRequest]:
        metadata = self.parse_request_metadata(lines)
        if not metadata:
            return None
            
        request = WorkRequest(
            request_metadata=metadata,
            final_status="COMPLETED"
        )
        
        # If not blacklisted, parse other information
        if not metadata.is_blacklisted:
            request.query_info = self.parse_query_info(lines)
            request.video_search = self.parse_video_search(lines)
            request.download_stats = self.parse_download_stats(lines)
        else:
            request.final_status = "BLACKLISTED"
            request.error_message = metadata.blacklist_reason
            
        return request

def main():
    logging.basicConfig(level=logging.INFO)
    parser = WorkerLogParser()
    
    # Parse the log file
    requests = parser.parse_log('example_worker.txt')
    
    # Write to JSON file
    with open('parsed_worker_log.json', 'w', encoding='utf-8') as f:
        json.dump(requests, f, indent=2)
    
    print(f"Parsed {len(requests)} requests to parsed_worker_log.json")

if __name__ == "__main__":
    main() 