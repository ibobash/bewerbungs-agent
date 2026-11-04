"""One command for a new personalized search from the chat."""
import argparse
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='Neue persönliche Suche mit Dashboard starten')
    parser.add_argument('--profile', type=Path)
    parser.add_argument('--report-dir', type=Path, default=Path('reports'))
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--skip-remotive', action='store_true')
    args = parser.parse_args()
    candidates = [args.profile, Path(os.environ['JOB_PROFILE_PATH']) if os.environ.get('JOB_PROFILE_PATH') else None,
                  Path('/workspace/private-job-profile.json'), Path('profile.json')]
    profile = next((p for p in candidates if p is not None and p.is_file()), None)
    if profile is None:
        parser.error('Kein persönliches Profil gefunden. Eine ungefilterte Ersatzsuche wird nicht gestartet.')
    from .daily import main as daily_main
    command = ['--profile', str(profile), '--report-dir', str(args.report_dir)]
    if args.refresh:
        command.append('--refresh')
    if args.skip_remotive:
        command.append('--skip-remotive')
    return daily_main(command)


if __name__ == '__main__':
    raise SystemExit(main())
