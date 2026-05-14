#!/usr/bin/env python
# -*- coding: utf-8 -*-
# iagitup - Download github repository and upload it to the Internet Archive with metadata.

# Copyright (C) 2017-2018 Giovanni Damiola
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

__author__     = "Giovanni Damiola"
__copyright__  = "Copyright 2018, Giovanni Damiola"
__main_name__  = 'iagitup'
__license__    = 'GPLv3'
__status__     = "Production/Stable"
__version__    = "v1.8"

import shutil
import argparse
import sys

from iagitup import iagitup

MAX_ERROR_LENGTH = 180

PROGRAM_DESCRIPTION = 'A tool to archive a GitHub repository to the Internet Archive. \
                       The script downloads the GitHub repository, creates a git bundle and uploads \
                       it to archive.org. https://github.com/gdamdam/iagitup'

# Configure argparser
parser = argparse.ArgumentParser(description=PROGRAM_DESCRIPTION)
parser.add_argument('--metadata', '-m', default=None, type=str, required=False, help='custom metadata to add to the archive.org item')
parser.add_argument('--s3-access', '-s3a', default=None, type=str, required=False, help='Internet Archive S3 access key (from https://archive.org/account/s3.php)')
parser.add_argument('--s3-secret', '-s3s', default=None, type=str, required=False, help='Internet Archive S3 secret key (from https://archive.org/account/s3.php)')
parser.add_argument('--version', '-v', action='version', version=__version__)
parser.add_argument('url', type=str, help='[GITHUB REPO] to archive')
args = parser.parse_args()


def repo_label_from_url(repo_url):
    parts = repo_url.rstrip('/').split('/')
    if len(parts) >= 2:
        return '/'.join(parts[-2:])
    return repo_url


def short_error(error):
    message = ' '.join(str(error).split())
    if len(message) > MAX_ERROR_LENGTH:
        return f'{message[:MAX_ERROR_LENGTH - 3]}...'
    return message


def short_skip_reason(reason):
    return {
        'already archived': 'exists',
        'archived less than one week ago': 'recent',
        'unchanged since the last archived snapshot': 'unchanged',
    }.get(reason, reason)


def main():
    if args.url == "":
        return

    s3_keys = None
    if args.s3_access is not None and args.s3_secret is not None:
        s3_keys = (args.s3_access, args.s3_secret)
    ia_session = iagitup.get_ia_session(s3_keys)

    repo_url = args.url
    repo_label = repo_label_from_url(repo_url)
    custom_metadata = args.metadata
    custom_meta_dict = None
    repo_dir = None

    try:
        repo_data, repo_dir = iagitup.repo_download(repo_url)
    except Exception as err:
        print(f"FAIL {repo_label}: download: {short_error(err)}")
        sys.exit(1)
    repo_label = repo_data['full_name']

    # parse supplemental metadata.
    if custom_metadata is not None:
        custom_meta_dict = {}
        for meta in custom_metadata.split(','):
            k, v = meta.split(':')
            custom_meta_dict[k] = v

    try:
        # upload the repo on IA
        identifier, _meta, _bundle_filename = iagitup.upload_ia(
            github_repo_folder=repo_dir,
            github_repo_data=repo_data,
            ia_session=ia_session,
            custom_meta=custom_meta_dict)
    except iagitup.ArchiveSkipped as skipped:
        if skipped.next_archive_at is not None:
            until = skipped.next_archive_at.strftime('%Y-%m-%d')
            print(f"SUCCESS {repo_label}: skipped recent until {until} (ia:{skipped.identifier})")
        else:
            print(f"SUCCESS {repo_label}: skipped {short_skip_reason(skipped.reason)} (ia:{skipped.identifier})")
    except iagitup.InternetArchiveRateLimitError as err:
        print(f"FAIL {repo_label}: IA rate limit: {short_error(err)}")
        sys.exit(iagitup.IA_RATE_LIMIT_EXIT_CODE)
    except Exception as err:
        print(f"FAIL {repo_label}: archive: {short_error(err)}")
        sys.exit(1)
    else:
        print(f"SUCCESS {repo_label}: archived (ia:{identifier})")
    finally:
        if repo_dir is not None:
            shutil.rmtree(repo_dir, ignore_errors=True)


if __name__ == '__main__':
    main()
