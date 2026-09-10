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
    """ Videoning necha soniya ekanligini aniqlaydi """
    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path
    ]
    process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE)
    stdout, _ = await process.communicate()
    try:
        return float(stdout.decode().strip())
    except:
        return 0.0

async def add_audio_to_video(video_path: str, audio_path: str, output_path: str) -> bool:
    cmd = [
        "ffmpeg", "-y", "-i", video_path, "-i", audio_path,
        "-map", "0:v", "-map", "1:a", "-map", "0:a?",
        "-c:v", "copy", "-c:a", "aac", "-disposition:a:0", "default", output_path
    ]
    process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    await process.communicate()
    return process.returncode == 0

async def add_subtitle_to_video(video_path: str, subtitle_path: str, output_path: str) -> bool:
    cmd = [
        "ffmpeg", "-y", "-i", video_path, "-i", subtitle_path,
        "-map", "0:v", "-map", "0:a?", "-map", "1:s", "-map", "0:s?",
        "-c", "copy", "-disposition:s:0", "default", output_path
    ]
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

# ---> YANGILANGAN LETTERBOXING <---
async def apply_letterbox(
    video_path: str, 
    output_path: str, 
    tracker,
    total_duration: float,
    crf: int = 18, 
    preset: str = "slow"
) -> bool:
    
    pad_filter = "pad=ceil(max(iw\\,ih*(16/9))/2)*2:ceil(max(ih\\,iw/(16/9))/2)*2:(ow-iw)/2:(oh-ih)/2:black"
    
    cmd = [
        "ffmpeg", "-y", "-i", video_path, "-map", "0",
        "-vf", pad_filter, "-c:v", "libx264", "-preset", preset,
        "-crf", str(crf), "-profile:v", "high", "-c:a", "copy", "-c:s", "copy",
        "-progress", "pipe:1",  # Progressni stdout ga chiqaradi
        "-nostats",             # Oddiy terminal axlatlarini yashiradi
        output_path
    ]
    
    # DEVNULL qilinishi juda muhim, aks holda bufer to'lib dastur qotib qoladi
    process = await asyncio.create_subprocess_exec(
        *cmd, 
        stdout=asyncio.subprocess.PIPE, 
        stderr=asyncio.subprocess.DEVNULL
    )
    
    while True:
        # Stdout'dan FFmpeg yozayotgan qatorlarni asinxron o'qiymiz
        line = await process.stdout.readline()
        if not line:
            break
            
        line_str = line.decode().strip()
        
        # FFmpeg har soniyada qancha vaqtni qayta ishlaganini ushlaymiz (microseconds)
        if line_str.startswith("out_time_us="):
            try:
                out_time_us = int(line_str.split("=")[1])
                current_seconds = out_time_us / 1000000.0
                
                # Tracker orqali Telegramga xabar beramiz
                await tracker.update_ffmpeg(current_seconds, total_duration)
            except Exception as e:
                # Agar foydalanuvchi "Bekor qilish" bossa, jarayonni majburiy o'ldiramiz
                if str(e) == "TaskCancelled":
                    process.terminate()
                    await process.wait()
                    raise
                pass
                
    await process.wait()
    # Natija majburiy uzilmagan bo'lsa va kod 0 bo'lsa, muvaffaqiyatli
    return process.returncode == 0