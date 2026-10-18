import re, sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import bench

STOP = re.compile(r'(Chọn VnExpress|Chọn Báo|Tin liên quan|Bài liên quan|Bình luận|Xem thêm|Từ khóa|Bạn muốn Google|Các nguồn|Có thể bạn quan tâm|Tin mới|Đọc nhiều|Quan tâm nhất|Chia sẻ bài viết)', re.I)


def body(url, n=3500, start_after=None):
    t = bench.load(url)['text']
    m = re.search(r'^# .+$', t, re.M)
    s = t[m.start():] if m else t
    out = []
    for ln in s.splitlines():
        if STOP.search(ln) and sum(len(x) for x in out) > 800:
            break
        ln = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', ln).strip()
        if ln and not re.match(r'^[\*\-!]\s*$', ln) and not ln.startswith('![') and len(ln.split()) >= 3:
            out.append(ln)
    text = '\n'.join(out)
    return text[:n]


if __name__ == '__main__':
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 3500
    print(body(sys.argv[1], n))
