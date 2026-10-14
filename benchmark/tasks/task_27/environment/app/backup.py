import os


def create_backup(source_dir, archive_path):
    command = f"tar -czf {archive_path} {source_dir}"
    exit_code = os.system(command)
    return exit_code == 0
