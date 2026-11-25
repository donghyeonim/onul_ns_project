"""[실험] 이슈 카드를 짧은 영상(mp4)으로: 그래픽이 그려지는 4~5초 영상
사용법: python3 make_video.py cards.json 출력폴더 [이슈번호 ...]
→ 출력폴더/card_0N.mp4 (1080x1350, 30fps, 소리 없음). 이슈번호를 안 주면 모든 이슈.
인스타그램 캐러셀에는 사진과 영상을 섞어 올릴 수 있다.
"""
import json, os, shutil, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_cards as mc  # noqa: E402

FPS = 30
HOLD0, ANIM, HOLD1 = 0.5, 3.0, 2.5  # 처음 멈춤, 그려지는 시간, 끝 멈춤(초)


def ffmpeg_exe():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        sys.exit("ffmpeg이 없어요: pip install imageio-ffmpeg")


def render(d, it, idx, n, path):
    cmd = [ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{mc.W}x{mc.H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium",
           "-movflags", "+faststart", path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    total = int((HOLD0 + ANIM + HOLD1) * FPS)
    last = None
    for f in range(total):
        t = (f / FPS - HOLD0) / ANIM
        t = max(0.0, min(1.0, t))
        if last is None or t != last[0]:  # 멈춘 구간은 같은 그림 재사용
            last = (t, mc.issue_visual(d, it, idx, n, n + 2, progress=t).tobytes())
        proc.stdin.write(last[1])
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("영상 만들기 실패")
    print(path)


def main():
    d = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    n = len(d["issues"])
    pick = [int(x) for x in sys.argv[3:]] or list(range(1, n + 1))
    for i in pick:
        it = d["issues"][i - 1]
        if not it.get("visual"):
            print(f"이슈 {i}: 그래픽(visual)이 없어서 영상을 건너뜀")
            continue
        render(d, it, i, n, os.path.join(out, f"card_{i + 1:02d}.mp4"))


if __name__ == "__main__":
    main()
