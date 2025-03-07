import logging
import shutil
import os
import threading
import time
import gc
import psutil
import uuid
from qbittorrentapi import Client, LoginFailed, TorrentStates, exceptions
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from tqdm import tqdm
import requests

# Configuration
QB_HOST = "http://localhost:8080"
QB_USER = "admin"
QB_PASS = "password"
SAVE_PATH = r"C:\tmp\ubuntu_torrents"
MAX_ITERATIONS = 10000
MAX_WORKERS = 1
MAX_ACTIVE_TORRENTS = 1
LOGGING_INTERVAL = 5
TORRENT_URL = "https://releases.ubuntu.com/24.04/ubuntu-24.04.2-desktop-amd64.iso.torrent"
RETRY_ATTEMPTS = 10  # Increased retries  
CLEANUP_TIMEOUT = 15

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler = logging.FileHandler('ubuntu_stress_test.log', mode='w')
file_handler.setFormatter(formatter)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

_stop_flag = threading.Event()
semaphore = threading.Semaphore(MAX_ACTIVE_TORRENTS)

def validate_torrent_url(url: str) -> bool:
    """Verify torrent URL accessibility with exponential backoff"""
    for attempt in range(3):
        try:
            response = requests.head(url, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                logger.debug(f"URL validation successful: {url}")
                return True
            logger.error(f"Invalid status code {response.status_code} for {url}")
            return False
        except requests.exceptions.RequestException as e:
            logger.warning(f"URL validation failed (Attempt {attempt+1}/3): {e}")
            time.sleep(2 ** attempt)
    return False

def get_client(retries=5) -> Client:
    """Create authenticated client with retry logic"""
    for attempt in range(retries):
        try:
            client = Client(
                host=QB_HOST,
                username=QB_USER,
                password=QB_PASS,
                VERIFY_WEBUI_CERTIFICATE=False,
                REQUESTS_ARGS={'timeout': (30, 30)}
            )
            client.auth_log_in()
            logger.debug("Successfully authenticated with qBittorrent")
            return client
        except (LoginFailed, exceptions.APIError) as e:
            logger.error(f"Authentication failed (Attempt {attempt+1}/{retries}): {e}")
            time.sleep(2 ** attempt)
        except Exception as e:
            logger.error(f"Client creation failed: {str(e)}")
            time.sleep(5)
    raise SystemExit("Failed to create qBittorrent client")

def safe_delete(path: str) -> bool:
    """Process-safe deletion with extended retry logic and timeouts"""
    if not os.path.exists(path):
        return True

    for attempt in range(5):
        try:
            # Terminate processes holding the path
            for proc in psutil.process_iter(['pid', 'name', 'open_files']):
                if proc.info['name'].lower() in ('qbittorrent.exe', 'python.exe'):
                    continue
                if proc.info['open_files']:
                    for item in proc.info['open_files']:
                        if path.lower() in item.path.lower():
                            logger.warning(f"Killing PID {proc.pid} ({proc.name()}) holding {path}")
                            proc.kill()
                            proc.wait(timeout=5)
            # Attempt deletion
            shutil.rmtree(path, ignore_errors=True)
            if not os.path.exists(path):
                return True
        except (PermissionError, FileNotFoundError, OSError) as e:
            logger.debug(f"Deletion error (Attempt {attempt+1}/5): {e}")
            time.sleep(2 ** attempt)
    return False

def process_torrent(iteration: int, max_retries=3) -> None:
    """Robust torrent processing with retry logic"""
    client = None
    unique_id = str(uuid.uuid4())[:8]
    temp_dir = os.path.join(SAVE_PATH, f"temp_{iteration}_{unique_id}")
    category = f"stress_{unique_id}"
    torrent_hash = None

    with semaphore:
        for retry in range(max_retries):
            try:
                if _stop_flag.is_set():
                    return

                logger.info(f"Starting iteration {iteration} (Attempt {retry+1}/{max_retries})")
                os.makedirs(temp_dir, exist_ok=True)

                client = get_client()
                logger.debug("Client acquired successfully")

                # Add torrent with retries
                for add_attempt in range(3):
                    try:
                        client.torrents_add(
                            urls=[TORRENT_URL],
                            save_path=temp_dir,
                            category=category,
                            paused=True,
                            use_auto_torrent_management=False
                        )
                        break
                    except exceptions.APIError as e:
                        logger.warning(f"Torrent add failed (Attempt {add_attempt+1}/3): {e}")
                        time.sleep(5)
                else:
                    raise RuntimeError("Torrent add failed after retries")

                # Verify torrent registration
                for _ in range(10):
                    torrents = client.torrents_info(category=category)
                    if torrents:
                        torrent = torrents[0]
                        torrent_hash = torrent.hash
                        break
                    time.sleep(2)
                else:
                    raise TimeoutError("Torrent not found after add")

                # Resume and monitor
                client.torrents_resume(torrent_hashes=torrent_hash)
                start_time = time.time()

                while not _stop_flag.is_set():
                    torrent_info = client.torrents_info(torrent_hashes=torrent_hash)[0]
                    progress = round(torrent_info.progress * 100, 1)
                    dl_speed = torrent_info.dlspeed / 1e6

                    if torrent_info.state_enum in (TorrentStates.DOWNLOADING, TorrentStates.STALLED_DOWNLOAD):
                        logger.info(f"Iter {iteration}: {progress}% | {dl_speed:.2f} MB/s")

                    if progress >= 100:
                        client.torrents_pause(torrent_hashes=torrent_hash)
                        break

                    if torrent_info.state_enum == TorrentStates.ERROR:
                        raise RuntimeError(f"Torrent entered error state: {torrent_info.state}")

                    time.sleep(5)

                # Cleanup after successful download
                client.torrents_delete(delete_files=True, torrent_hashes=torrent_hash)
                if safe_delete(temp_dir):
                    logger.info(f"Iteration {iteration} completed successfully")
                    return
                else:
                    raise RuntimeError("Cleanup failed")

            except Exception as e:
                logger.error(f"Iteration {iteration} failed (Attempt {retry+1}/{max_retries}): {str(e)}")
                try:
                    if client and torrent_hash:
                        client.torrents_delete(torrent_hashes=torrent_hash)
                except:
                    pass
                if retry < max_retries - 1:
                    time.sleep(60)  # Wait before retry

        logger.error(f"Failed all {max_retries} attempts for iteration {iteration}")

def main():
    os.makedirs(SAVE_PATH, exist_ok=True)

    # Pre-validate URL
    if not validate_torrent_url(TORRENT_URL):
        logger.error("Invalid torrent URL")
        return

    # Pre-cleanup existing torrents
    try:
        client = get_client()
        existing = client.torrents_info(category="stress_*")
        if existing:
            client.torrents_delete(delete_files=True, torrent_hashes=[t.hash for t in existing])
    except Exception as e:
        logger.error(f"Pre-cleanup failed: {str(e)}")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = set()
        try:
            for i in range(1, MAX_ITERATIONS + 1):
                while len(futures) >= MAX_WORKERS * 2:
                    done, _ = wait(futures, timeout=0.1, return_when=FIRST_COMPLETED)
                    futures.difference_update(done)

                fut = executor.submit(process_torrent, i)
                futures.add(fut)
                time.sleep(0.5)

                if i % 50 == 0:
                    gc.collect()

        except KeyboardInterrupt:
            _stop_flag.set()
            logger.warning("Stopping operations...")
            for fut in futures:
                fut.cancel()
            executor.shutdown(wait=False)
            try:
                client = get_client()
                torrents = client.torrents_info(category="stress_*")
                client.torrents_delete(delete_files=True, torrent_hashes=[t.hash for t in torrents])
            except:
                pass
            raise

    # Final cleanup
    for _ in range(5):
        if safe_delete(SAVE_PATH):
            break
        time.sleep(5)
    logger.info("**** Execution completed ****")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
    finally:
        safe_delete(SAVE_PATH)
        logger.info("Final cleanup complete")