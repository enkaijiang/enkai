import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse


DATA = [
    {
        "type": "file",
        "name": "dify-guide.md",
        "path": r"D:\Docs",
        "size": 2048,
        "date_modified": "2026-05-14T00:00:00Z",
    },
    {
        "type": "file",
        "name": "project-plan.xlsx",
        "path": r"D:\Docs",
        "size": 4096,
        "date_modified": "2026-05-13T10:20:00Z",
    },
    {
        "type": "folder",
        "name": "Design",
        "path": r"D:\Projects",
        "size": 0,
        "date_modified": "2026-05-12T08:30:00Z",
    },
]


class MockEverythingHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        keyword = (query.get("search", [""])[0] or "").lower()
        count = int(query.get("count", ["10"])[0] or "10")

        filtered = []
        for item in DATA:
            haystack = f'{item["path"]}\\{item["name"]}'.lower()
            if keyword and keyword not in haystack:
                continue
            filtered.append(item)

        payload = {
            "totalResults": len(filtered),
            "results": filtered[:count],
        }

        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="本地模拟 Everything HTTP Server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18080)
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), MockEverythingHandler)
    print(f"Mock Everything server 已启动：http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
