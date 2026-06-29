from __future__ import annotations

from app.config import PROGRAMS


def main() -> None:
    for program in PROGRAMS:
        print(
            f"{program.code}\t{program.name}\tbudget={program.general_places}\tpaid={program.paid_places}"
        )


if __name__ == "__main__":
    main()

