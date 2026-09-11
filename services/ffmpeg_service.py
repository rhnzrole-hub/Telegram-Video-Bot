import asyncio
import json

async def get_video_streams(file_path: str) -> list:
    cmd = ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", file_path]
    process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE)
    stdout, _ = await process.communicate()
    try:
        data = json.loads(stdout)
        return data.get("streams", [])
    except:
        return []

async def get_video_duration(video_path: str) -> float:
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path]
    process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE)
    stdout, _ = await process.communicate()
    try:
        return float(stdout.decode().strip())
    except:
        return 0.0

async def add_audio_to_video(video_path: str, audio_path: str, output_path: str) -> bool:
    cmd = ["ffmpeg", "-y", "-i", video_path, "-i", audio_path, "-map", "0:v", "-map", "1:a", "-map", "0:a?", "-c:v", "copy", "-c:a", "aac", "-disposition:a:0", "default", output_path]
    process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    await process.communicate()
    return process.returncode == 0

async def add_subtitle_to_video(video_path: str, subtitle_path: str, output_path: str) -> bool:
    cmd = ["ffmpeg", "-y", "-i", video_path, "-i", subtitle_path, "-map", "0:v", "-map", "0:a?", "-map", "1:s", "-map", "0:s?", "-c", "copy", "-disposition:s:0", "default", output_path]
    process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    await process.communicate()
    return process.returncode == 0

async def apply_multiple_metadata(video_path: str, changes: dict, output_path: str) -> bool:
    cmd = ["ffmpeg", "-y", "-i", video_path, "-map", "0", "-c", "copy"]
    for str_idx, meta in changes.items():
        for key, val in meta.items():
            cmd.extend([f"-metadata:s:{str_idx}", f"{key}={val}"])
    cmd.append(output_path)
    process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    await process.communicate()
    return process.returncode == 0

async def apply_letterbox(video_path: str, output_path: str, tracker, total_duration: float, start_time: float = 0.0, duration: float = None, crf: int = 18, preset: str = "ultrafast") -> bool:
    pad_filter = "pad=ceil(max(iw\\,ih*(16/9))/2)*2:ceil(max(ih\\,iw/(16/9))/2)*2:(ow-iw)/2:(oh-ih)/2:black"
    
    cmd = ["ffmpeg", "-y"]
    if start_time > 0: cmd.extend(["-ss", str(start_time)])
    if duration: cmd.extend(["-t", str(duration)])
    cmd.extend(["-i", video_path])
        
    cmd.extend(["-map", "0", "-vf", pad_filter, "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p", "-threads", "1", "-c:a", "copy", "-c:s", "copy", "-progress", "pipe:1", "-nostats", output_path])
    
    process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    
    while True:
        line = await process.stdout.readline()
        if not line: break
        line_str = line.decode().strip()
        if line_str.startswith("out_time_us="):
            try:
                out_time_us = int(line_str.split("=")[1])
                current_seconds = out_time_us / 1000000.0
                await tracker.update_ffmpeg(current_seconds, total_duration)
            except Exception as e:
                if str(e) == "TaskCancelled":
                    process.terminate()
                    await process.wait()
                    raise
                pass
                
    await process.wait()
    return process.returncode == 0