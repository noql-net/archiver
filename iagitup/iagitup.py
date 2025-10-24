#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

__author__     = "Giovanni Damiola"
__copyright__  = "Copyright 2018, Giovanni Damiola"
__main_name__  = 'iagitup'
__license__    = 'GPLv3'
__version__    = "v1.8"

import os
import subprocess
import shutil
import json
from internetarchive import get_session
import git
import requests
from datetime import datetime
from markdown2 import markdown_path


def mkdirs(path):
    """Make directory, if it doesn't exist."""
    if not os.path.exists(path):
        os.makedirs(path)

# download the github repo
def repo_download(github_repo_url):
    """Downloads a GitHub repo locally.

       arguments:
            github_repo_url -- the GitHub repo home url

       returns:
            github_repo_data, github_repo_dir - the repo details and the local repo directory
    """
    download_dir = os.path.expanduser('~/.iagitup/downloads')
    mkdirs(os.path.expanduser('~/.iagitup'))
    mkdirs(download_dir)

    # parsing url to initialize the github api rul and get the repo_data
    gh_user, gh_repo = github_repo_url.split('/')[3:]
    gh_api_url = "https://api.github.com/repos/{}/{}".format(gh_user, gh_repo)

    # delete the temp directory if exists
    github_repo_dir = os.path.join(download_dir, gh_repo)
    if os.path.exists(github_repo_dir):
        shutil.rmtree(github_repo_dir)

    # get the data from GitHub api
    headers = {}
    if 'GITHUB_TOKEN' in os.environ:
        headers['Authorization'] = 'Bearer {0}'.format(os.environ['GITHUB_TOKEN'])

    req = requests.get(gh_api_url, headers=headers)
    if req.status_code == 200:
        github_repo_data = json.loads(req.text)
        # download the repo from github
        github_repo_dir = os.path.join(download_dir, gh_repo)
        try:
            git.Git().clone(github_repo_data['clone_url'], github_repo_dir)
        except Exception as e:
            print(f'Error occurred while downloading: {github_repo_url}')
            print(str(e))
            exit(1)
    else:
        raise ValueError(f'Error occurred while downloading: {github_repo_url}. Status code: {req.status_code}')

    return github_repo_data, github_repo_dir


def get_description_from_readme(gh_repo_folder):
    """From the GitHub repo returns html description from the README.md or readme.txt

        arguments:
                gh_repo_folder -- the repo local folder path

        returns:
                description -- html description
    """
    path = os.path.join(gh_repo_folder, 'README.md')
    path3 = os.path.join(gh_repo_folder, 'readme.md')
    path2 = os.path.join(gh_repo_folder, 'readme.txt')
    description = ''
    if os.path.exists(path):
        description = markdown_path(path)
        description = description.replace('\n', '')
    elif os.path.exists(path3):
        description = markdown_path(path3)
        description = description.replace('\n', '')
    elif os.path.exists(path2):
        with open(path2, 'r') as f:
            description = f.readlines()
            description =' '.join(description)
    return description

def create_bundle(gh_repo_folder, repo_name):
    """creates the gir repository bundle to upload

        arguments:
            gh_repo_folder  --  the repo local folder path
            repo_name       --  the repo name

        returns:
            bundle_path     --  the path to the bundle file
    """
    print(gh_repo_folder, repo_name)
    if os.path.exists(gh_repo_folder):
        main_pwd = os.getcwd()
        os.chdir(gh_repo_folder)
        bundle_name = '{}.bundle'.format(repo_name)
        subprocess.check_call(['git', 'bundle', 'create', bundle_name, '--all'])
        bundle_path = os.path.join(gh_repo_folder, bundle_name)
        os.chdir(main_pwd)
    else:
        raise ValueError('Error creating bundle, directory does not exist: {}'.format(gh_repo_folder))
    return bundle_path

def upload_ia(*, github_repo_folder, github_repo_data, ia_session, custom_meta=None):
    """Uploads the bundle to the Internet Archive.

        arguments:
                github_repo_folder  -- path to the bundle
                github_repo_data    -- repository metadata
                custom_meta     -- custom metadata

        returns:
                item_name        -- Internet Archive item identifier
                meta            -- the item metadata
                bundle_filename -- the git bundle filename
    """
    # formatting some dates string
    pushed = datetime.strptime(github_repo_data['pushed_at'], '%Y-%m-%dT%H:%M:%SZ')
    pushed_date = pushed.strftime('%Y-%m-%d_%H-%M-%S')
    raw_pushed_date = pushed.strftime('%Y-%m-%d %H:%M:%S')
    date = pushed.strftime('%Y-%m-%d')
    year = pushed.strftime('%Y')

    # preparing some names
    repo_name = github_repo_data['full_name'].replace('/', '-')
    original_url = github_repo_data['html_url']
    bundle_filename = '{}_-_{}'.format(repo_name, pushed_date)

    # preparing some description
    description_footer = f'To restore the repository download the bundle <pre><code>wget https://archive.org/download/github.com-{bundle_filename}/{bundle_filename}.bundle</code></pre> and run: <pre><code> git clone {bundle_filename}.bundle </code></pre>'
    description = f'<br/> {github_repo_data['description']} <br/><br/> {get_description_from_readme(github_repo_folder)} <br/>{description_footer}'

    # preparing uploader metadata
    uploader_url = github_repo_data['owner']['html_url']
    uploader_name = github_repo_data['owner']['login']

    # let's grab the avatar too
    uploader_avatar_url = github_repo_data['owner']['avatar_url']
    pic = requests.get(uploader_avatar_url, stream = True)
    uploader_avatar_path = os.path.join(github_repo_folder, 'cover.jpg')
    with open(uploader_avatar_path, 'wb') as f:
        pic.raw.decode_content = True
        shutil.copyfileobj(pic.raw, f)

    # some Internet Archive Metadata
    collection = 'open_source_software'
    mediatype = 'software'
    subject = 'GitHub;code;software;git'

    uploader = f'{__main_name__} - {__version__}'

    description = f'{description} <br/><br/>Source: <a href="{original_url}">{original_url}</a><br/>Uploader: <a href="{uploader_url}">{uploader_name}</a><br/>Upload date: {date}'

    ## Creating bundle file of  the  git repo
    try:
        bundle_file = create_bundle(github_repo_folder, bundle_filename)
    except ValueError as err:
        print(str(err))
        shutil.rmtree(github_repo_folder)
        exit(1)

    # inizializing the internet archive item name
    # here we set the ia identifier
    item_name = f'github.com-{repo_name}_-_{pushed_date}'
    title = item_name

    #initializing the main metadata
    meta = dict(
        mediatype=mediatype,
        creator=uploader_name,
        collection=collection,
        title=title,
        year=year,
        date=date,
        subject=subject,
        uploaded_with=uploader,
        originalurl=original_url,
        pushed_date=raw_pushed_date,
        description=description
    )

    # override default metadata with any supplemental metadata provided.
    if custom_meta is not None:
        meta.update(custom_meta)

    try:
        # upload the item to the Internet Archive
        print(f"Creating item on Internet Archive: {meta['title']}")
        item = ia_session.get_item(item_name)
        # checking if the item already exists:
        if not item.exists:
            print(f"Uploading file to the internet archive: {bundle_file}")
            item.upload(bundle_file, metadata=meta, retries=3, verbose=True, delete=False)
            # upload the item to the Internet Archive
            print("Uploading avatar...")
            item.upload(os.path.join(github_repo_folder, 'cover.jpg'), retries=3, verbose=True, delete=True)
        else:
            print("\nSTOP: The same repository seems already archived.")
            print(f"---->>  Archived repository URL: \n \thttps://archive.org/details/{item_name}")
            print(f"---->>  Archived git bundle file: \n \thttps://archive.org/download/{item_name}/{bundle_filename}.bundle \n\n")
            shutil.rmtree(github_repo_folder)
            exit(0)

    except Exception as e:
        print(str(e))
        shutil.rmtree(github_repo_folder)
        exit(1)

    # return item identifier and metadata as output
    return item_name, meta, bundle_filename

def get_ia_session(s3_keys = None):
    """creates an ia (Internet Archive) session. If no s3_keys is provided tries to configure ia interactively.

        arguments:
            s3_keys   --  tuple (access, secret) for S3 access (optional)
        returns:
            ia session or None if no s3 keys are provided and interactive configuration fails.
    """
    if s3_keys is not None:
        return get_session(config={'s3': {'access': s3_keys[0], 'secret': s3_keys[1]}})

    config_file = os.path.expanduser('~/.config/ia.ini')
    if not os.path.exists(config_file):
        # fallback config file
        config_file = os.path.expanduser('~/.ia')

    if not os.path.exists(config_file):
        msg = '\nWARNING - It looks like you need to configure your Internet Archive account!\n \
        for registration go to https://archive.org/account/login.createaccount.php\n'
        print(msg)
        try:
            failed = subprocess.call(["ia", "configure"])
            if failed:
                exit(1)
        except Exception as e:
            msg = f'\nSomething went wrong trying to configure your internet archive account.\n Error - {str(e)}'
            print(msg)
            exit(1)

    return get_session(config_file=config_file)
