"""
ytdlp-icli.py
    An interactive commandline wrapper for yt-dlp.

Author:             Fabian Bartl
E-Mail:             fabian@informatic-freak.de
Repository:         https://github.com/FabianBartl/ytdlp-interactive-cli
Last major update:  01.03.2025

Requirements:
    - pick          # not pypick !
    - quantiphy
    - colorama

Used Tools:
    - https://github.com/yt-dlp/yt-dlp
    - https://ffmpeg.org/ffmpeg.html
    - https://github.com/aisk/pick

License:
    MIT License

    Copyright (c) 2025 Fabian Bartl

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
"""

import os
import json
import pick
import subprocess as sp

from quantiphy import Quantity
from pathlib import Path
from typing import Optional, Union, Any

from colorama import Fore, Style
from colorama import init as colorama_init
colorama_init(autoreset=True)

ENV = os.environ
CONFIG = {
    "ffmpeg_bin": "ffmpeg",
    "ytdlp_bin": "yt-dlp",
    "audio_format": "best",
    "video_format": "best",
    "thumbnail_format": None,
    "output_dirpath": Path.home() / "Downloads",        # set to own download path
}


def get_quantity(number: Any, model: str, info: Optional[str] = None, **kwargs) -> str:
    try:
        number = float(number)
    except:
        if not info is None:
            return info
        number = 0
    return Quantity(number, model, **kwargs)


def print_command(command: Union[list[str], str]) -> None:
    if isinstance(command, list):
        command = " ".join([ str(e) for e in command ])
    print(f"{Style.DIM}$ {command}")

def run_command(command: list[str], **kwargs) -> sp.CompletedProcess:
    global ENV
    kwargs = {"encoding": "utf-8", "errors": "replace", "universal_newlines": True, "env": ENV, **kwargs}
    print_command(command)
    return sp.run(command, capture_output=True, **kwargs)


def request_ytdlp_metadata(yturl: str) -> dict:
    global CONFIG
    command = [CONFIG["ytdlp_bin"], "-j", yturl]
    process = run_command(command)
    if process.returncode != 0:
        print(f"{Fore.RED}Critical error:")
        print(process.stderr)
        exit()
    metadata = json.loads(process.stdout)
    
    formats = {"audio": [], "video": [], "image": [], "metadata": metadata}

    for fmt in metadata.get("formats"):
        if not fmt.get("format_id", "").strip().isdigit():
            continue
        
        if fmt.get("acodec", "none") != "none":
            formats["audio"].append(fmt)
        elif fmt.get("vcodec", "none") != "none":
            formats["video"].append(fmt)

    for fmt in metadata.get("thumbnails"):
        if fmt.get("resolution"):
            formats["image"].append(fmt)
    
    return formats

def ytdlp_download(yturl: str, fmt: str, ytdlp_args: list[str] = []) -> int:
    global CONFIG, ENV
    command = [CONFIG["ytdlp_bin"], "-f", fmt, yturl, *ytdlp_args]
    print_command(command)
    process = sp.Popen(command, env=ENV)
    return process.wait()

def ffmpeg_remux(file: Path, *, audio_only: bool = False) -> Path:
    global CONFIG, ENV
    outpath = file.with_suffix(f".remux{file.suffix}")
    command = [CONFIG["ffmpeg_bin"], "-i", str(file.resolve()), "-c", "copy", "-c:a", "aac", str(outpath.resolve())]
    print_command(command)
    process = sp.Popen(command, env=ENV)
    process.wait()
    return outpath


def pick_yt_audio_format(formats: list[dict], *, default: Optional[str] = None) -> str:
    options = [
        pick.Option("best audio", "bestaudio"),
        pick.Option("no audio", None),
    ]
    for fmt in formats:
        fmt["filesize"] = get_quantity(fmt.get("filesize"), "B", "N/A")
        fmt["abr"] = get_quantity(fmt.get("abr"), "", "N/A")
        fmt["asr"] = get_quantity(fmt.get("asr"), "Hz")

        text = f"id: {str(fmt.get('format_id', 'N/A')):<5}  codec: {str(fmt.get('acodec', 'N/A')):<10}  ext: {str(fmt.get('audio_ext', 'N/A')):<5}  lang: {str(fmt.get('language', 'N/A')):<3}  bitrate: {str(fmt.get('abr', 'N/A')):<7}  sample rate: {str(fmt.get('asr', 'N/A')):<10}  filesize: {str(fmt.get('filesize', 'N/A')):<10}"
        options.append(pick.Option(text, fmt.get("format_id")))

    default_index = 0
    if not default is None:
        for ind, option in enumerate(options):
            if option.value == default:
                default_index = ind
                break

    selected = pick.pick(options,
        title="Select audio",
        indicator="*",
        default_index=default_index,
        multiselect=False,
        min_selection_count=1,
        clear_screen=True,
    )
    return selected[0].value

def pick_yt_video_format(formats: list[dict], *, default: Optional[str] = None) -> str:
    options = [
        pick.Option("best video", "bestvideo"),
        pick.Option("no video", None),
    ]
    for fmt in formats:
        fmt["filesize"] = get_quantity(fmt.get("filesize"), "B", "N/A")
        fmt["vbr"] = get_quantity(fmt.get("vbr"), "")
        fmt["wxh"] = "{width}x{height}".format(**fmt)

        text = f"id: {str(fmt.get('format_id', 'N/A')):<5}  codec: {str(fmt.get('vcodec', 'N/A')):<15}  ext: {str(fmt.get('video_ext', 'N/A')):<5}  format: {str(fmt.get('wxh', 'N/A')):<10}  bitrate: {str(fmt.get('vbr', 'N/A')):<10}  fps: {str(fmt.get('fps', 'N/A')):<4}  filesize: {str(fmt.get('filesize', 'N/A')):<10}"
        options.append(pick.Option(text, fmt.get("format_id")))

    default_index = 0
    if not default is None:
        for ind, option in enumerate(options):
            if option.value == default:
                default_index = ind
                break

    selected = pick.pick(options,
        title="Select video",
        indicator="*",
        default_index=default_index,
        multiselect=False,
        min_selection_count=1,
        clear_screen=True,
    )
    return selected[0].value

def pick_yt_thumbnail_format(metadata: dict, *, default: Optional[str] = None) -> tuple[str, list[str]]:
    options = [
        pick.Option("best thumbnail", "best"),
        pick.Option("embed thumbnail", "embed", description="Supported filetypes for thumbnail embedding are: mp3, mp4"),
        pick.Option("no thumbnail", None),
    ]

    default_index = 2
    if not default is None:
        for ind, option in enumerate(options):
            if option.value == default:
                default_index = ind
                break

    selected = pick.pick(options,
        title="Select thumbnail",
        indicator="*",
        default_index=default_index,
        multiselect=False,
        min_selection_count=1,
        clear_screen=True
    )
    
    if selected[0].value == "best":
        ytdlp_arg = ["--write-thumbnail", "--convert-thumbnails", "jpg"]
    elif selected[0].value == "embed":
        ytdlp_arg = ["--embed-thumbnail"]
    else:
        ytdlp_arg = []
    
    return (selected[0].value, ytdlp_arg)


def check_dependency_path(expected_path: Path, error_message: str) -> bool:
    try:
        command = [expected_path]
        process = run_command(command)
    except FileNotFoundError:
        print(error_message)
        return False
    return True


def main() -> None:
    global CONFIG
    
    outdir = CONFIG["output_dirpath"].absolute()
    if not outdir.exists():
        print(f"{Fore.RED}output directory not found: [edit line 64 to change it]")
        print(str(outdir))
        return
    print_command(["cd", outdir])
    os.chdir(str(outdir))
    
    if not check_dependency_path(CONFIG["ffmpeg_bin"], "ffmpeg not found"):
        return
    if not check_dependency_path(CONFIG["ytdlp_bin"], "yt-dlp not found"):
        return
    
    input_url = input("YouTube URL: ").strip()
    yturl = input_url

    metadata = request_ytdlp_metadata(yturl)
    filename = metadata.get("metadata").get("filename")
    filepath = Path(filename)

    audio_format = pick_yt_audio_format(metadata.get("audio"), default=CONFIG.get("audio_format"))
    video_format = pick_yt_video_format(metadata.get("video"), default=CONFIG.get("video_format"))
    thumbnail_format = pick_yt_thumbnail_format(metadata.get("metadata"), default=CONFIG.get("thumbnail_format"))
    
    audio_only = (audio_format and not video_format)
    ytdlp_args = [*thumbnail_format[1]]

    if audio_only:
        ytdlp_args.extend(["-x", "--audio-format", "mp3"])
        filepath = filepath.with_suffix(".mp3")
    else:
        ytdlp_args.extend(["--merge-output-format", "mp4"])
        filepath = filepath.with_suffix(".mp4")

    fmt = filter(bool, [audio_format, video_format])
    ytdlp_download(yturl, "+".join(fmt), ytdlp_args)
    if not filepath.exists():
        print(f"{Fore.RED}downloaded file not found, expected it here:")
        print(str(filepath))
        return
    
    if not thumbnail_format[0] is None:
        print(f"{Fore.GREEN}thumbnail stored here:\n", str(filepath.with_suffix(".jpg").absolute()))
    print(f"{Fore.GREEN}download stored here:\n", str(filepath.absolute()))
    
    # remux_path = ffmpeg_remux(filepath, audio_only=audio_only)
    # print(f"{Fore.GREEN}remuxed output stored here:\n", str(remux_path.absolute()))

    input("press ENTER to exit\n")


if __name__ == "__main__":
    main()
