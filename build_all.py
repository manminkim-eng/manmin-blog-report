# -*- coding: utf-8 -*-
"""
매월 초 통합 갱신 러너 (블로그 + 유튜브 한 번에)
사용법:
  python build_all.py --month 2026-07 [--period "2026.07 월간"]
                      [--blog-src "<블로그 xlsx 폴더>"] [--yt-src "<유튜브 csv 상위폴더>"]
동작:
  1) 블로그 월 인덱스 재생성 (build_month.py)  - blog-src 없으면 <month>/data 사용
  2) 유튜브 월 인덱스 재생성 (youtube/build_youtube.py) - yt-src 없으면 youtube/<month>/data 사용
  3) 양쪽 랜딩 자동 갱신 + GoatCounter 스니펫 존재 점검
끝나면 GitHub Desktop에서 Commit -> Push 하면 끝.
"""
import argparse, subprocess, sys, os, glob
REPO = os.path.dirname(os.path.abspath(__file__))

def run(cmd, cwd):
    print(">>", " ".join(cmd), f"(cwd={os.path.relpath(cwd, REPO) or '.'})")
    r = subprocess.run(cmd, cwd=cwd)
    if r.returncode:
        print("[오류] 명령 실패"); sys.exit(r.returncode)

def check_snippet():
    miss = []
    for f in glob.glob(os.path.join(REPO, "index.html")) + \
             glob.glob(os.path.join(REPO, "*", "index.html")) + \
             glob.glob(os.path.join(REPO, "youtube", "index.html")) + \
             glob.glob(os.path.join(REPO, "youtube", "*", "index.html")):
        try:
            if "manmin.goatcounter.com" not in open(f, encoding="utf-8").read():
                miss.append(os.path.relpath(f, REPO))
        except Exception:
            pass
    print("[GoatCounter] 스니펫 누락:", miss if miss else "없음(전부 정상)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", required=True)
    ap.add_argument("--period", default="")
    ap.add_argument("--blog-src", default="")
    ap.add_argument("--yt-src", default="")
    a = ap.parse_args()
    period = a.period or a.month.replace("-", ".") + " 월간"

    blog_src = a.blog_src or os.path.join(REPO, a.month, "data")
    if os.path.isdir(blog_src):
        run([sys.executable, "build_month.py", "--src", blog_src, "--month", a.month, "--period", period], REPO)
    else:
        print(f"[건너뜀] 블로그 데이터 없음: {blog_src}")

    yt = os.path.join(REPO, "youtube")
    yt_src = a.yt_src or os.path.join(yt, a.month, "data")
    if os.path.isdir(yt_src):
        run([sys.executable, "build_youtube.py", "--src", yt_src, "--month", a.month, "--period", period], yt)
    else:
        print(f"[건너뜀] 유튜브 데이터 없음: {yt_src}")

    check_snippet()

    # NAS Web Station 자동 배포 → 밖에서 Tailscale ON 후 http://100.123.66.123/manmin-blog/ 로 열람.
    #   정슬래시(//) UNC 사용(이 환경에서 역슬래시 \\ UNC는 파이썬에서 실패). data/스크립트/캐시는 제외.
    #   NAS 미접속이어도 갱신이 멈추지 않도록 try/except.
    try:
        import shutil
        WEB_DEST = "//MANMIN-NAS/web/manmin-blog"
        shutil.copytree(REPO, WEB_DEST, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__", "*.py", "*.pyc", "data", ".git"))
        print("[NAS 배포] 완료:", WEB_DEST)
    except Exception as ex:
        print("[NAS 배포] 건너뜀(무시하고 계속):", repr(ex))

    print("\n[완료] 블로그·유튜브 갱신 완료. GitHub Desktop에서 Commit -> Push origin 하세요.")
