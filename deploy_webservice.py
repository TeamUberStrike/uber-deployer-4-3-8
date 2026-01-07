import paramiko
from scp import SCPClient
from dotenv import load_dotenv
import os
import argparse
from urllib.parse import urlparse
import time
from paramiko.ssh_exception import SSHException, NoValidConnectionsError
import logging
from datetime import datetime


def main():
    args = parse_arguments()
    local_logger, remote_logger = initialize_logger()

    load_dotenv()  # loads .env from current directory
    
    host = os.getenv("HOST")
    user = os.getenv("USER")
    password = os.getenv("PASS")
    port = int(os.getenv("PORT", 22))

    ssh = establish_ssh_connection(
        host=host,
        user=user,
        password=password,
        port=port,
    )

    remote_deploy_path = "C:/production/"
    cmd = f'powershell -Command "New-Item -ItemType Directory -Path {remote_deploy_path} -Force"'
    ssh_execute(ssh, cmd, remote_logger)
   
    with SCPClient(ssh.get_transport()) as scp:
       scp.put("setupWindowsWebservice.ps1", remote_deploy_path)
       scp.put("setupWindowsPorts.ps1", remote_deploy_path)
   

    if args.path:
        path = os.path.expanduser(args.path)
        path = os.path.abspath(path)

        if not os.path.exists(path):
            parser.error(f"Path does not exist: {path}")

        local_logger.info(f"local path to copy: {path}")

    if args.url:
        parsed = urlparse(args.url)
        if not parsed.scheme:
            parser.error(f"Invalid URL: {args.url}")
        error_message = "download url not yet implemented"
        local_logger.error(error_message)
        sys.exit(error_message)
        local_logger.info(f"URL selected: {args.url}")

    basename = os.path.basename(os.path.normpath(path))
    with SCPClient(ssh.get_transport()) as scp:
        scp.put(path, remote_deploy_path, recursive=True)
    if basename != "Artifacts":
        cmd = f'powershell -Command Remove-Item -Path "{remote_deploy_path}/Artifacts" -Recurse -Force'
        ssh_execute(ssh, cmd, remote_logger)
        cmd = f'powershell -Command Rename-Item -Path "{remote_deploy_path}/{basename}" -NewName "Artifacts"'
        ssh_execute(ssh, cmd, remote_logger)

    setup_ports_command = f'cd {remote_deploy_path} && powershell -NoProfile -ExecutionPolicy Bypass -File "{remote_deploy_path}setupWindowsPorts.ps1"'
    ssh_execute(ssh, setup_ports_command, remote_logger)

    setup_webservice_command = f'cd {remote_deploy_path} && powershell -NoProfile -ExecutionPolicy Bypass -File "{remote_deploy_path}setupWindowsWebservice.ps1"'
    ssh_execute(ssh, setup_webservice_command, remote_logger)
 
    ssh.close()

def parse_arguments():
    parser = argparse.ArgumentParser(description="Requires ssh variables set in .env: HOST, USER, PASS and optionally PORT. Use either --path or --url")

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        "--path",
        help="Local filesystem path"
    )

    group.add_argument(
        "--url",
        help="Remote URL (http, https, ftp, etc.)"
    )

    return parser.parse_args()


def establish_ssh_connection(host, user, password=None, key_file=None, port=22,
    retries=3600,
    delay=5,
    timeout=10,
):
    last_exc = None

    for attempt in range(1, retries + 1):
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=host,
                username=user,
                password=password,
                port=port,
                key_filename=key_file,
            )
            stdin, stdout, stderr = client.exec_command("echo ok")
            if stdout.read().strip() == b"ok":
                print("SSH connection established...")
                return client
        
        except (SSHException, NoValidConnectionsError, OSError) as e:
            last_exc = e
            print(f"SSH attempt {attempt}/{retries} failed: {e}")
            time.sleep(delay)

    raise RuntimeError("SSH not available after retries") from last_exc

def ssh_execute(ssh, cmd, logger, accept_error=True):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    logger.info(f"command: {cmd}")
    logger.info(f"output: {stdout.read().decode()}")
    rc = stdout.channel.recv_exit_status()
    if rc != 0:
        logger.error(f"output: {stderr.read().decode()}")
        if accept_error is False:
            raise RuntimeError(stderr.read().decode())


def initialize_logger():
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Log file name with date & time (DD-MM-YYYY_HH-MM-SS)
    timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    log_file = os.path.join(log_dir, f"deploy_{timestamp}.log")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%d-%m-%Y %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # also log to console
        ],
    )
    
    return logging.getLogger("local"), logging.getLogger("remote")

if __name__ == "__main__":
    main()

