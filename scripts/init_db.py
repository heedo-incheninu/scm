"""로컬 SQLite 데이터베이스를 초기화한다."""

from __future__ import annotations

import argparse

from scm.database import initialize_database


def main() -> None:
    parser = argparse.ArgumentParser(description="SCM PoC 표본 데이터베이스 초기화")
    parser.add_argument("--database", default="data/scm.db", help="SQLite 파일 경로")
    parser.add_argument("--seed", type=int, default=20260622, help="표본 데이터 난수 시드")
    parser.add_argument("--replace", action="store_true", help="기존 데이터를 교체")
    args = parser.parse_args()
    path = initialize_database(args.database, seed=args.seed, replace=args.replace)
    print(f"초기화 완료: {path}")


if __name__ == "__main__":
    main()
