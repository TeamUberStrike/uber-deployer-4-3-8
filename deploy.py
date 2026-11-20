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
import sys


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
        logger=local_logger,
        password=password,
        port=port,
    )

    remote_deploy_path = "C:/production/"
    cmd = f'powershell -Command "New-Item -ItemType Directory -Path {remote_deploy_path} -Force"'
    ssh_execute(ssh, cmd, remote_logger)

    with SCPClient(ssh.get_transport()) as scp:
        scp.put("setupWindowsWebservice.ps1", remote_deploy_path)
        scp.put("setupWindowsPorts.ps1", remote_deploy_path)
        scp.put("setupWindowsPortal.ps1", remote_deploy_path)
        scp.put("setupWindowsCallback.ps1", remote_deploy_path)

    if args.path:
        path = os.path.expanduser(args.path)
        path = os.path.abspath(path)

        if not os.path.exists(path):
            local_logger.error(f"Path does not exist: {path}")
            sys.exit(1)

        local_logger.info(f"local path to copy: {path}")

    if args.url:
        parsed = urlparse(args.url)
        if not parsed.scheme:
            local_logger.error(f"Invalid URL: {args.url}")
        error_message = "download url not yet implemented"
        local_logger.error(error_message)
        sys.exit(error_message)
        local_logger.info(f"URL selected: {args.url}")

    deploy_path = resolve_deploy_path(path, args.service_type, local_logger)

    if args.service_type == "callback":
        remote_artifacts_path = f"{remote_deploy_path}Artifacts"
        cmd = f'powershell -Command "New-Item -ItemType Directory -Path {remote_artifacts_path} -Force"'
        ssh_execute(ssh, cmd, remote_logger)
        with SCPClient(ssh.get_transport()) as scp:
            scp.put(deploy_path, remote_artifacts_path, recursive=True)
    else:
        basename = os.path.basename(os.path.normpath(deploy_path))
        with SCPClient(ssh.get_transport()) as scp:
            scp.put(deploy_path, remote_deploy_path, recursive=True)
        if basename != "Artifacts":
            cmd = f'powershell -Command Remove-Item -Path "{remote_deploy_path}/Artifacts" -Recurse -Force'
            ssh_execute(ssh, cmd, remote_logger)
            cmd = f'powershell -Command Rename-Item -Path "{remote_deploy_path}/{basename}" -NewName "Artifacts"'
            ssh_execute(ssh, cmd, remote_logger)

    setup_ports_command = f'cd {remote_deploy_path} && powershell -NoProfile -ExecutionPolicy Bypass -File "{remote_deploy_path}setupWindowsPorts.ps1"'
    ssh_execute(ssh, setup_ports_command, remote_logger)

    if args.service_type == "webservice":
        setup_webservice_command = f'cd {remote_deploy_path} && powershell -NoProfile -ExecutionPolicy Bypass -File "{remote_deploy_path}setupWindowsWebservice.ps1"'
        if args.webservice_hostname:
            setup_webservice_command += f' "{args.webservice_hostname}"'
        ssh_execute(ssh, setup_webservice_command, remote_logger)
    elif args.service_type == "portal":
        setup_portal_command = f'cd {remote_deploy_path} && powershell -NoProfile -ExecutionPolicy Bypass -File "{remote_deploy_path}setupWindowsPortal.ps1"'
        if args.webservice_hostname:
            setup_portal_command += f' "{args.webservice_hostname}"'
        ssh_execute(ssh, setup_portal_command, remote_logger)
    elif args.service_type == "callback":
        cert_thumbprint = args.cert_thumbprint or ""
        cert_remote_path = ""
        cert_password = args.cert_password if args.cert_password is not None else os.getenv("CERT_PASSWORD", "")

        if args.cert_pfx:
            cert_pfx_path = os.path.abspath(os.path.expanduser(args.cert_pfx))
            if not os.path.isfile(cert_pfx_path):
                local_logger.error(f"Certificate file does not exist: {cert_pfx_path}")
                sys.exit(1)
            with SCPClient(ssh.get_transport()) as scp:
                scp.put(cert_pfx_path, remote_deploy_path)
            cert_remote_path = f"{remote_deploy_path}{os.path.basename(cert_pfx_path)}"
            local_logger.info(f"certificate uploaded: {cert_remote_path}")

        hostname = args.webservice_hostname or ""
        setup_callback_command = f'cd {remote_deploy_path} && powershell -NoProfile -ExecutionPolicy Bypass -File "{remote_deploy_path}setupWindowsCallback.ps1" "{hostname}" "{cert_thumbprint}" "{cert_remote_path}" "{cert_password}"'
        ssh_execute(ssh, setup_callback_command, remote_logger)

    ssh.close()


def resolve_deploy_path(path, service_type, logger):
    if service_type != "callback":
        return path

    if os.path.basename(os.path.normpath(path)) == "Cmune.Channels.Callback":
        callback_path = path
    else:
        callback_path = os.path.join(path, "Cmune.Channels.Callback")

    if not os.path.isdir(callback_path):
        logger.error(f"Callback path does not exist: {callback_path}")
        sys.exit(1)

    return callback_path


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Requires ssh variables set in .env: HOST, USER, PASS and optionally PORT. Use either --path or --url"
    )

    parser.add_argument(
        "service_type",
        choices=["webservice", "portal", "callback"],
        help="Type of service to deploy"
    )

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument("--path", help="Local filesystem path")

    group.add_argument("--url", help="Remote URL (http, https, ftp, etc.)")

    parser.add_argument(
        "--webservice-hostname",
        help="Hostname for the site (host name or domain)"
    )

    cert_group = parser.add_mutually_exclusive_group()

    cert_group.add_argument(
        "--cert-thumbprint",
        help="Thumbprint of an existing certificate in LocalMachine\\My for the HTTPS binding"
    )

    cert_group.add_argument(
        "--cert-pfx",
        help="Local path to a PFX file (e.g. Cloudflare Origin Certificate) to import"
    )

    parser.add_argument(
        "--cert-password",
        help="Password for the PFX (defaults to CERT_PASSWORD from .env)"
    )

    return parser.parse_args()


def establish_ssh_connection(
    host,
    user,
    logger,
    password=None,
    key_file=None,
    port=22,
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
                logger.info(
                    f"SSH connection established to {user}@{host} at port: {port}..."
                )
                return client

        except (SSHException, NoValidConnectionsError, OSError) as e:
            last_exc = e
            logger.info(f"SSH attempt {attempt}/{retries} failed: {e}")
            time.sleep(delay)
    error_message = "SSH not available after retries"
    logger.error(error_message)
    raise RuntimeError(error_message) from last_exc


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
    log_file = os.path.join(log_dir, f"deploy_webservice_{timestamp}.log")

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%d-%m-%Y %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),  # also log to console
        ],
    )

    return logging.getLogger("local"), logging.getLogger("remote")


if __name__ == "__main__":
    main()
