import glob
import importlib
import os
from datetime import datetime

from config import GRAPHANA_REGION_DATA, VM_BASE_PATH, VM_HOST, VM_PASSWORD, VM_USERNAME

DATA_FOLDERS = [region for region in GRAPHANA_REGION_DATA.keys()]


def _latest_file(pattern):
    files = glob.glob(pattern, recursive=True)
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def _find_latest_reports():
    latest_txt = _latest_file(os.path.join("reports", "**", "*_humio_service_monitoring.txt"))
    latest_pdf = _latest_file(os.path.join("reports", "**", "service_monitoring*.pdf"))
    return latest_txt, latest_pdf


def _sftp_mkdir_p(sftp, remote_path):
    parts = remote_path.strip("/").split("/")
    current = ""
    for part in parts:
        current += "/" + part
        try:
            sftp.stat(current)
        except FileNotFoundError:
            sftp.mkdir(current)


def _sftp_upload_directory(sftp, local_dir, remote_dir):
    _sftp_mkdir_p(sftp, remote_dir)
    for root, _, files in os.walk(local_dir):
        rel_path = os.path.relpath(root, local_dir)
        remote_root = remote_dir if rel_path == "." else f"{remote_dir}/{rel_path.replace(os.sep, '/')}"
        _sftp_mkdir_p(sftp, remote_root)
        for filename in files:
            local_path = os.path.join(root, filename)
            remote_path = f"{remote_root}/{filename}"
            sftp.put(local_path, remote_path)


def move_reports_and_data_to_vm():
    latest_txt, latest_pdf = _find_latest_reports()

    files_to_move = []
    if latest_txt and os.path.isfile(latest_txt):
        files_to_move.append(latest_txt)
    if latest_pdf and os.path.isfile(latest_pdf):
        files_to_move.append(latest_pdf)

    folders_to_move = [folder for folder in DATA_FOLDERS if os.path.isdir(folder)]

    if not files_to_move and not folders_to_move:
        print("No report files or data folders found to move.")
        return False

    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
    remote_dir = f"{VM_BASE_PATH}/data_{timestamp}"

    try:
        paramiko = importlib.import_module("paramiko")
    except ImportError:
        print("ERROR: paramiko is not installed. Run: pip install paramiko")
        return False

    ssh = None
    sftp = None
    moved_any = False
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=VM_HOST,
            username=VM_USERNAME,
            password=VM_PASSWORD,
            timeout=30,
        )

        sftp = ssh.open_sftp()
        _sftp_mkdir_p(sftp, remote_dir)

        for file_path in files_to_move:
            remote_file = f"{remote_dir}/{os.path.basename(file_path)}"
            sftp.put(file_path, remote_file)
            print(f"Uploaded file: {file_path} -> {remote_file}")
            moved_any = True
            print(f"Moved file : {file_path}")

        for folder in folders_to_move:
            remote_folder = f"{remote_dir}/{folder}"
            _sftp_upload_directory(sftp, folder, remote_folder)
            print(f"Uploaded folder: {folder} -> {remote_folder}")
            moved_any = True
            print(f"Moved folder: {folder}")

        print(f"\nAll artifacts moved to VM path: {remote_dir}")
        print("\n\033[1mPlease check slack channel #test-hack for analysis results. This may take upto 5 minutes.\033[0m")
        print("If it fails, please check AI-report-analysis/output/auto_analysis.log on the target VM for details.")
        return moved_any
    except Exception as e:
        print(f"ERROR while moving reports/data to VM: {e}")
        print("\n\n\033[1mPlease resolve the error and run this script with --upload-only to move the generated reports to the VM.\033[0m")
        return False
    finally:
        if sftp:
            sftp.close()
        if ssh:
            ssh.close()
