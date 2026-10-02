from __future__ import annotations

import csv
import ctypes
import hashlib
import json
import os
import re
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable


CHUNK_SIZE = 1024 * 1024
SYSTEM_DIRECTORIES = {
    "$recycle.bin",
    "config.msi",
    "msocache",
    "perflogs",
    "program files",
    "program files (x86)",
    "programdata",
    "recovery",
    "system volume information",
    "windows",
}


@dataclass(frozen=True)
class DriveInfo:
    root: str
    label: str
    kind: str
    total_bytes: int
    free_bytes: int


@dataclass(frozen=True)
class FileRecord:
    path: str
    name: str
    size: int
    created: float
    modified: float


@dataclass(frozen=True)
class DuplicateGroup:
    name: str
    size: int
    algorithm: str
    digest: str
    files: tuple[FileRecord, ...]


ScanProgress = Callable[[int, int], None]
HashProgress = Callable[[int, int], None]


def _candidate_name(name: str) -> str:
    path = Path(name)
    stem = re.sub(r"\s*(?:-\s*(?:kopya|copy)|\s*\(\d+\))$", "", path.stem, flags=re.IGNORECASE)
    return f"{stem}{path.suffix}".casefold()


def _drive_label(root: str) -> str:
    if os.name != "nt":
        return root
    volume_name = ctypes.create_unicode_buffer(261)
    try:
        success = ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(root), volume_name, len(volume_name), None, None, None, None, 0
        )
        return volume_name.value if success and volume_name.value else root
    except (AttributeError, OSError):
        return root


def list_drives(include_removable: bool = False) -> list[DriveInfo]:
    """List fixed disks, and optionally removable USB-style volumes on Windows."""
    drives: list[DriveInfo] = []
    if os.name == "nt":
        logical_mask = ctypes.windll.kernel32.GetLogicalDrives()
        for drive_index in range(26):
            if not logical_mask & (1 << drive_index):
                continue
            root = f"{chr(65 + drive_index)}:\\"
            drive_type = ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(root))
            if drive_type == 3:
                kind = "Fixed"
            elif drive_type == 2 and include_removable:
                kind = "USB / Harici"
            else:
                continue
            try:
                usage = shutil.disk_usage(root)
            except OSError:
                continue
            drives.append(
                DriveInfo(root, _drive_label(root), kind, usage.total, usage.free)
            )
        return drives

    mount = "/"
    try:
        usage = shutil.disk_usage(mount)
    except OSError:
        return drives
    return [DriveInfo(mount, mount, "Fixed", usage.total, usage.free)]


def _is_hidden_or_system(entry: os.DirEntry[str]) -> bool:
    if entry.name.startswith("."):
        return True
    if os.name != "nt":
        return False
    try:
        attributes = ctypes.windll.kernel32.GetFileAttributesW(ctypes.c_wchar_p(entry.path))
        if attributes == 0xFFFFFFFF:
            return False
        return bool(attributes & (0x2 | 0x4))
    except (AttributeError, OSError):
        return False


def scan_files(
    roots: Iterable[str],
    min_size_bytes: int,
    extensions: set[str] | None,
    include_hidden: bool,
    progress: ScanProgress,
    cancelled: Callable[[], bool],
) -> dict[tuple[str, int], list[FileRecord]]:
    """Walk drives with scandir and return same-name/same-size candidates only."""
    candidates: dict[tuple[str, int], list[FileRecord]] = {}
    normalized_extensions = None if extensions is None else {extension.casefold() for extension in extensions}
    file_count = 0
    folder_count = 0
    scanned_entries = 0

    for root_text in roots:
        root = os.path.abspath(root_text)
        pending = [root]
        while pending and not cancelled():
            current = pending.pop()
            try:
                with os.scandir(current) as entries:
                    for entry in entries:
                        if cancelled():
                            break
                        scanned_entries += 1
                        if scanned_entries % 100 == 0:
                            progress(file_count, folder_count)
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                folder_count += 1
                                is_root_child = os.path.normcase(current) == os.path.normcase(root)
                                if is_root_child and entry.name.casefold() in SYSTEM_DIRECTORIES:
                                    continue
                                if not include_hidden and _is_hidden_or_system(entry):
                                    continue
                                pending.append(entry.path)
                                continue
                            if not entry.is_file(follow_symlinks=False):
                                continue
                            if not include_hidden and _is_hidden_or_system(entry):
                                continue
                            file_count += 1
                            suffix = Path(entry.name).suffix.casefold()
                            if normalized_extensions is not None and suffix not in normalized_extensions:
                                continue
                            stat = entry.stat(follow_symlinks=False)
                            if stat.st_size < min_size_bytes:
                                continue
                            key = (_candidate_name(entry.name), stat.st_size)
                            candidates.setdefault(key, []).append(
                                FileRecord(
                                    path=entry.path,
                                    name=entry.name,
                                    size=stat.st_size,
                                    created=getattr(stat, "st_ctime", stat.st_mtime),
                                    modified=stat.st_mtime,
                                )
                            )
                        except (OSError, PermissionError):
                            continue
            except (OSError, PermissionError):
                continue
    progress(file_count, folder_count)
    return {key: files for key, files in candidates.items() if len(files) > 1}


def find_duplicates(
    candidates: dict[tuple[str, int], list[FileRecord]],
    algorithm: str,
    progress: HashProgress,
    cancelled: Callable[[], bool],
) -> list[DuplicateGroup]:
    """Hash only pre-filtered name/size groups and retain matching digests."""
    total = sum(len(files) for files in candidates.values())
    completed = 0
    duplicates: list[DuplicateGroup] = []
    for (normalized_name, size), files in candidates.items():
        if cancelled():
            break
        by_digest: dict[str, list[FileRecord]] = {}
        for record in files:
            if cancelled():
                break
            hasher = hashlib.new(algorithm.casefold())
            try:
                with open(record.path, "rb") as stream:
                    for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
                        hasher.update(chunk)
                by_digest.setdefault(hasher.hexdigest(), []).append(record)
            except OSError:
                pass
            completed += 1
            progress(completed, total)
        for digest, matching_files in by_digest.items():
            if len(matching_files) > 1:
                duplicates.append(
                    DuplicateGroup(
                        name=matching_files[0].name,
                        size=size,
                        algorithm=algorithm.upper(),
                        digest=digest,
                        files=tuple(matching_files),
                    )
                )
    return duplicates


def export_results(groups: list[DuplicateGroup], destination: str) -> None:
    path = Path(destination)
    suffix = path.suffix.casefold()
    if suffix == ".json":
        payload = [
            {
                "name": group.name,
                "size_bytes": group.size,
                "algorithm": group.algorithm,
                "digest": group.digest,
                "files": [asdict(record) for record in group.files],
            }
            for group in groups
        ]
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    elif suffix == ".csv":
        with path.open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.writer(stream)
            writer.writerow(["group", "name", "size_bytes", "algorithm", "digest", "path", "created"])
            for group_index, group in enumerate(groups, start=1):
                for record in group.files:
                    writer.writerow(
                        [group_index, group.name, group.size, group.algorithm, group.digest, record.path, record.created]
                    )
    else:
        lines = ["Kopya dosya raporu", "=" * 48, ""]
        for group_index, group in enumerate(groups, start=1):
            lines.extend(
                [
                    f"Grup {group_index}: {group.name} | {group.size:,} bayt | {group.algorithm}: {group.digest}",
                    *(f"  {record.path}" for record in group.files),
                    "",
                ]
            )
        path.write_text("\n".join(lines), encoding="utf-8")


def send_to_trash(path: str) -> None:
    from send2trash import send2trash as move_to_trash

    move_to_trash(path)


def move_file(source: str, destination_folder: str) -> str:
    destination = Path(destination_folder) / Path(source).name
    if destination.exists():
        raise FileExistsError(f"Hedefte aynı adlı dosya zaten var: {destination}")
    return shutil.move(source, str(destination))


def rename_file(source: str, new_name: str) -> str:
    if not new_name.strip() or Path(new_name).name != new_name or new_name in {".", ".."}:
        raise ValueError("Geçerli bir dosya adı girin.")
    destination = Path(source).with_name(new_name)
    if destination.exists():
        raise FileExistsError(f"Aynı adlı dosya zaten var: {destination}")
    return str(Path(source).rename(destination))