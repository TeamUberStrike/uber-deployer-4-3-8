import paramiko
from scp import SCPClient
from dotenv import load_dotenv
import os
import argparse
from urllib.parse import urlparse
import time
from paramiko.ssh_exception import SSHException, NoValidConnectionsError


def main():
    args = parse_arguments()

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
    ssh.exec_command(
        f'powershell -Command "New-Item -ItemType Directory -Path {remote_deploy_path} -Force"'
    )
   
    with SCPClient(ssh.get_transport()) as scp:
       scp.put("setupWindowsWebservice.ps1", remote_deploy_path)
       scp.put("setupWindowsPorts.ps1", remote_deploy_path)
   

    if args.path:
        path = os.path.expanduser(args.path)
        path = os.path.abspath(path)

        if not os.path.exists(path):
            parser.error(f"Path does not exist: {path}")

        print(f"Path selected: {path}")

    if args.url:
        parsed = urlparse(args.url)
        if not parsed.scheme:
            parser.error(f"Invalid URL: {args.url}")
        sys.exit("download url not yet implemented")
        print(f"URL selected: {args.url}")

    basename = os.path.basename(os.path.normpath(path))
    with SCPClient(ssh.get_transport()) as scp:
        scp.put(path, remote_deploy_path, recursive=True)
    if basename != "Artifacts":
        cmd = f'powershell -Command Remove-Item -Path "{remote_deploy_path}/Artifacts" -Recurse -Force'
        ssh.exec_command(cmd)
        cmd = f'powershell -Command Rename-Item -Path "{remote_deploy_path}/{basename}" -NewName "Artifacts"'
        ssh.exec_command(cmd)


    setup_ports_command = f'cd {remote_deploy_path} && powershell -NoProfile -ExecutionPolicy Bypass -File "{remote_deploy_path}setupWindowsPorts.ps1"'
    print(setup_ports_command)
    ssh.exec_command(setup_ports_command)

    setup_webservice_command = f'cd {remote_deploy_path} && powershell -NoProfile -ExecutionPolicy Bypass -File "{remote_deploy_path}setupWindowsWebservice.ps1"'
    print(setup_webservice_command)
    ssh.exec_command(setup_webservice_command)
 
    ssh.close()

def parse_arguments():
    parser = argparse.ArgumentParser(description="Use either --path or --url")

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

if __name__ == "__main__":
    main()

