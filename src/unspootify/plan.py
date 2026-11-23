"""Turn settings + a playlist into a sockseek run: input file, jobs, manifest, arguments."""

from __future__ import annotations

import csv
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

from unspootify.paths import self_command
from unspootify.settings import Settings
from unspootify.store import Track


@dataclass
class Job:
    """One unit sockseek works on. Songs: one track. Albums: one album. Artist: one artist."""

    snum: int  # 1-based line in the input file
    artist: str
    album: str = ""
    title: str = ""
    indexes: list[int] = field(default_factory=list)  # playlist rows this job covers
    number: int | None = None  # track number for naming (songs mode: playlist position)


@dataclass
class RunPlan:  # noqa: D101
    mode: str  # songs | albums | artist
    input_path: Path
    manifest_path: Path
    args: list[str]
    jobs: list[Job]
    library: Path


def pick_tracks(tracks: list[Track], settings: Settings, only: list[int] | None = None) -> list[Track]:
    """Which rows this run should try: unfinished ones, limited by Skip first / Only first."""
    adv = settings.advanced
    rows = tracks[adv.skip_n or 0 :]
    if adv.first_n:
        rows = rows[: adv.first_n]
    if only is not None:
        wanted = set(only)
        return [t for t in rows if t.index in wanted]
    return [t for t in rows if t.state not in ("done", "skipped", "failed")]


def make_jobs(mode: str, tracks: list[Track]) -> list[Job]:
    jobs: list[Job] = []
    if mode == "songs":
        for t in tracks:
            jobs.append(Job(len(jobs) + 1, t.artist, t.album, t.title, [t.index], number=t.index + 1))
    elif mode == "albums":
        by_album: dict[tuple[str, str], Job] = {}
        for t in tracks:
            key = (t.artist.lower(), (t.album or t.title).lower())
            if key not in by_album:
                by_album[key] = Job(len(by_album) + 1, t.artist, t.album or t.title)
            by_album[key].indexes.append(t.index)
        jobs = list(by_album.values())
    elif mode == "artist":
        by_artist: dict[str, Job] = {}
        for t in tracks:
            key = t.artist.lower()
            if key and key not in by_artist:
                by_artist[key] = Job(len(by_artist) + 1, t.artist)
            if key:
                by_artist[key].indexes.append(t.index)
        jobs = list(by_artist.values())
    else:
        raise ValueError(mode)
    return jobs


def write_input(mode: str, jobs: list[Job], tracks_by_index: dict[int, Track], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if mode == "artist":
        # sockseek list file: one quoted search per line; -g turns each into an artist discography
        path.write_text("".join(f'"artist={j.artist.replace(chr(34), "")}"\n' for j in jobs), encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if mode == "albums":  # title-less rows are album downloads
            w.writerow(["Artist", "Album"])
            for j in jobs:
                w.writerow([j.artist, j.album])
        else:
            w.writerow(["Artist", "Title", "Album", "Length"])
            for j in jobs:
                t = tracks_by_index[j.indexes[0]]
                w.writerow([t.artist, t.title, t.album, round(t.length_ms / 1000) if t.length_ms else ""])


def build_args(
    settings: Settings, *, mode: str, input_path: Path, stage: Path, index_path: Path, manifest_path: Path,
    format_override: str | None = None, force_override: bool | None = None, try_harder: bool | None = None,
    mock_dir: Path | None = None, config_path: Path | None = None,
) -> list[str]:
    o, adv = settings.options, settings.advanced
    fmt = format_override or o.format
    force = o.mode == "force" if force_override is None else force_override
    args = [str(input_path), "--input-type", "list" if mode == "artist" else "csv",
            "-p", str(stage), "--index-path", str(index_path), "--progress-json", "--no-progress"]
    # Login lives in a private per-run config file (never on the command line, where `ps` shows it).
    # Using our own config also means a stray ~/.config/sockseek/sockseek.conf can't change behaviour.
    args += ["--config", str(config_path)] if config_path else ["--no-config"]
    if mock_dir is not None:
        args += ["--mock-files-dir", str(mock_dir)]
    if mode == "artist":
        args.append("-g")
    if mode in ("albums", "artist") and o.album_art:
        args += ["--album-art", "largest"]
    args += ["--format", fmt] if force else ["--pref-format", fmt]
    if o.skip_existing:
        # Songs: also skip anything already in the library. Albums/artists: rely on sockseek's index only,
        # otherwise owning one song of an album counts as owning the album.
        if mode == "songs":
            args += ["--skip-music-dir", settings.library_path]
    else:
        args.append("--no-skip-existing")
    if o.try_harder if try_harder is None else try_harder:
        args.append("-d")
    if adv.fast:
        args.append("--fast-search")
    if adv.strict_title:
        args.append("--strict-title")
    if adv.min_bitrate:
        args += ["--min-bitrate", str(adv.min_bitrate)]
    if adv.listen_port:
        args += ["--listen-port", str(adv.listen_port)]
    # Stage files under a neutral name, then our finalize step moves them into the library
    # with the house naming scheme and tells sockseek's index where they went.
    # ({snum} identifies songs; album/artist jobs are identified by source artist/album in the path.)
    args += ["--name-format", "{snum}" if mode == "songs" else "{sartist}/{salbum|(_)}/{slsk-foldername}/{slsk-filename}"]
    finalize = " ".join(f'"{part}"' for part in [*self_command(), "finalize", str(manifest_path)])
    args += ["--on-complete", f'when=success scope=track update-index -- {finalize} {{snum}} "{{path}}"']
    return args


def write_config(path: Path, settings: Settings, offline: bool) -> None:
    """Private sockseek config with the login (0600, deleted after the run)."""
    user = settings.username or ("offline-test" if offline else "")
    password = settings.password or ("offline-test" if offline else "")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(f"username = {user.strip()}\npassword = {password}\n")


def write_manifest(path: Path, *, mode: str, library: Path, stage: Path, jobs: list[Job]) -> None:
    path.write_text(json.dumps({"mode": mode, "library": str(library), "stage": str(stage),
                                "jobs": [asdict(j) for j in jobs]}), encoding="utf-8")


def prepare(
    settings: Settings, playlist_id: str, tracks: list[Track], run_dir: Path, *, only: list[int] | None = None,
    format_override: str | None = None, force_override: bool | None = None, try_harder: bool | None = None,
    mock_dir: Path | None = None, extra_args: list[str] | None = None,
) -> RunPlan:
    mode = settings.options.grab
    chosen = pick_tracks(tracks, settings, only)
    jobs = make_jobs(mode, chosen)
    by_index = {t.index: t for t in tracks}
    input_path = run_dir / ("input.txt" if mode == "artist" else "input.csv")
    manifest = run_dir / "manifest.json"
    write_input(mode, jobs, by_index, input_path)
    library = Path(settings.library_path).expanduser()
    write_manifest(manifest, mode=mode, library=library, stage=run_dir / "stage", jobs=jobs)
    config = run_dir / "sockseek.conf"
    write_config(config, settings, offline=mock_dir is not None)
    args = build_args(
        settings, mode=mode, input_path=input_path, stage=run_dir / "stage",
        index_path=run_dir.parent / f"index-{playlist_id}-{mode}.csv", manifest_path=manifest,
        format_override=format_override, force_override=force_override, try_harder=try_harder, mock_dir=mock_dir,
        config_path=config,
    ) + list(extra_args or [])
    return RunPlan(mode, input_path, manifest, args, jobs, library)
