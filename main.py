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

from iagitup import iagitup

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

def main():
    s3_keys = None
    if args.s3_access is not None and args.s3_secret is not None:
        s3_keys = (args.s3_access, args.s3_secret)
    ia_session = iagitup.get_ia_session(s3_keys)

    repo_url = args.url
    custom_metadata = args.metadata
    custom_meta_dict = None

    print(f":: Downloading {repo_url} repository...")
    repo_data, repo_dir = iagitup.repo_download(repo_url)

    # parse supplemental metadata.
    if custom_metadata is not None:
        custom_meta_dict = {}
        for meta in custom_metadata.split(','):
            k, v = meta.split(':')
            custom_meta_dict[k] = v

    # upload the repo on IA
    identifier, meta, bundle_filename = iagitup.upload_ia(
        github_repo_folder=repo_dir,
        github_repo_data=repo_data,
        ia_session=ia_session,
        custom_meta=custom_meta_dict)

    # cleaning
    shutil.rmtree(repo_dir)

    # output
    print("\n:: Upload FINISHED. Item information:")
    print(f"Identifier: {meta['title']}")
    print(f"Archived repository URL: \n \thttps://archive.org/details/{identifier}")
    print(f"Archived git bundle file: \n \thttps://archive.org/download/{identifier}/{bundle_filename}.bundle \n\n")


if __name__ == '__main__':
    main()

