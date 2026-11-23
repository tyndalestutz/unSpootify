import sys

from unspootify.cli import COMMANDS

if len(sys.argv) > 1 and sys.argv[1] in COMMANDS:
    from unspootify.cli import main

    raise SystemExit(main(sys.argv[1:]))

from unspootify.app import main  # noqa: E402

raise SystemExit(main())
