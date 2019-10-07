import argparse
import logging.config

from druid.ui import DruidUI


def main():
    logging.config.dictConfig({
        'version': 1,
        'formatters': {
            'detailed': {
                'class': 'logging.Formatter',
                'format': '%(asctime)s %(name)-15s %(levelname)-8s'
                '%(processName)-10s %(message)s'
            },
        },
        'handlers': {
            'file': {
                'class': 'logging.FileHandler',
                'filename': 'druid.log',
                'mode': 'w',
                'formatter': 'detailed',
            },
        },
        'loggers': {
            'druid.io.crow': {
                'handlers': ['file'],
            },
            'druid.io.grid': {
                'handlers': ['file'],
            },
            'druid.io.screen': {
                'handlers': [],
            },
        },
        'root': {
            'level': 'DEBUG',
            'propagate': False,
            'handlers': [],
        },
    })

    parser = argparse.ArgumentParser()
    DruidUI().command(parser)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
