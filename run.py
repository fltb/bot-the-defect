import asyncio
import logging
import argparse

from adapters.cli_adapter import main as cli_main
from adapters.onebot_adapter import main as onebot_main

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logging.getLogger('apscheduler').setLevel(logging.WARNING)

def parse_args():
    parser = argparse.ArgumentParser(description='Run the chatbot with different adapters')
    parser.add_argument(
        '--adapter',
        choices=['cli', 'onebot'],
        default='onebot',
        help='Choose which adapter to run (default: onebot)'
    )
    return parser.parse_args()


def main():
    setup_logging()
    args = parse_args()

    if args.adapter == 'cli':
        asyncio.run(cli_main())
    else:
        # OneBot runs in synchronous mode
        onebot_main()

if __name__ == "__main__":
    main()