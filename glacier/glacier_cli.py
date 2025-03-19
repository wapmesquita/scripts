import boto3
import click
import json
from tqdm import tqdm
import os
import hashlib
from botocore.utils import calculate_tree_hash
from datetime import datetime, timedelta
import yaml
import time

CACHE_FILE = '.cache.yml'

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return yaml.safe_load(f)
    return {}

def save_cache(data):
    with open(CACHE_FILE, 'w') as f:
        yaml.safe_dump(data, f)

def store_in_cache(key, value):
    cache = load_cache()
    cache[key] = value
    save_cache(cache)

def clear_cache():
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)

@click.group(invoke_without_command=True)
@click.option('--verbose', is_flag=True, help="Show detailed responses.")
@click.option('--clear-cache', is_flag=True, help="Clear the cache.")
@click.pass_context
def cli(ctx, verbose, clear_cache):
    """A CLI to interact with AWS S3 Glacier."""
    if clear_cache:
        clear_cache()
        click.echo("Cache cleared.")
        return

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        return

    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose

    cache = load_cache()
    if 'region' in cache:
        ctx.obj['region'] = cache['region']
    else:
        ctx.obj['region'] = 'us-east-1'

    ctx.obj['region'] = click.prompt("Enter AWS region", default=ctx.obj['region'])
    store_in_cache('region', ctx.obj['region'])

    if 'profile' in cache:
        ctx.obj['profile'] = cache['profile']
    else:
        ctx.obj['profile'] = click.prompt("Enter AWS profile", default='default')
        store_in_cache('profile', ctx.obj['profile'])

    ctx.obj['vault_name'] = choose_vault(ctx)

def verbose_log(ctx, obj):
    """Print verbose log if verbose flag is set."""
    if ctx.obj['verbose']:
        try:
            click.echo(json.dumps(obj, indent=2))
        except TypeError:
            click.echo(str(obj))

def choose_vault(ctx):
    """Prompt the user to choose a vault."""
    session = boto3.Session(profile_name=ctx.obj['profile'])
    client = session.client('glacier', region_name=ctx.obj['region'])
    response = client.list_vaults()
    verbose_log(ctx, response)
    vaults = response.get('VaultList', [])
    if not vaults:
        click.echo("No vaults found.")
        return None
    click.echo("Select a vault:")
    for i, vault in enumerate(vaults):
        click.echo(f"{i + 1}. {vault['VaultName']}")
    choice = click.prompt("Enter the number of the vault you want to select", type=int)
    if 1 <= choice <= len(vaults):
        return vaults[choice - 1]['VaultName']
    else:
        click.echo("Invalid choice.")
        return None

@cli.command()
@click.pass_context
def jobs(ctx):
    """List jobs in a Glacier vault."""
    vault_name = ctx.obj['vault_name']
    if not vault_name:
        return
    session = boto3.Session(profile_name=ctx.obj['profile'])
    client = session.client('glacier', region_name=ctx.obj['region'])
    response = client.list_jobs(vaultName=vault_name)
    click.echo(json.dumps(response, indent=2))

@cli.command()
@click.pass_context
def upload_abort(ctx):
    """Abort a multipart upload in a Glacier vault."""
    vault_name = ctx.obj['vault_name']
    if not vault_name:
        return
    upload_id = click.prompt("Enter upload ID")
    session = boto3.Session(profile_name=ctx.obj['profile'])
    client = session.client('glacier', region_name=ctx.obj['region'])
    response = client.abort_multipart_upload(vaultName=vault_name, uploadId=upload_id)
    click.echo(json.dumps(response, indent=2))
    return response

@cli.command()
@click.argument('file_path')
@click.pass_context
def upload_multipart(ctx, file_path):
    """Upload a file to a Glacier vault using multipart upload."""
    vault_name = ctx.obj['vault_name']
    if not vault_name:
        return
    file_name = os.path.basename(file_path)
    session = boto3.Session(profile_name=ctx.obj['profile'])
    client = session.client('glacier', region_name=ctx.obj['region'])
    file_size = os.path.getsize(file_path)
    part_size = 8 * 1024 * 1024  # 8 MB
    checksum = hashlib.sha256()

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    log_filename = f"{file_name}_{timestamp}_{vault_name}.log"

    result_obj = {}

    try:
        original_checksum = calculate_tree_hash(open(file_path, 'rb'))
        result_obj['original_checksum'] = original_checksum
        result_obj['file_size'] = file_size
        result_obj['part_size'] = part_size

        # Initiate multipart upload
        response = client.initiate_multipart_upload(vaultName=vault_name, archiveDescription=file_name, partSize=str(part_size))
        result_obj['initiate_multipart_upload'] = response
        result_obj['parts'] = {}
        verbose_log(ctx, response)

        upload_id = response['uploadId']

        try:
            with open(file_path, 'rb') as f:
                part_number = 1
                with tqdm(total=file_size, unit='B', unit_scale=True, desc=file_path) as pbar:
                    while True:
                        part_data = f.read(part_size)
                        if not part_data:
                            break
                        start_byte = part_size * (part_number - 1)
                        end_byte = start_byte + len(part_data) - 1
                        response = client.upload_multipart_part(vaultName=vault_name, uploadId=upload_id, range=f'bytes {start_byte}-{end_byte}/*', body=part_data)
                        result_obj['parts'][f'{part_number}'] = response
                        checksum.update(part_data)
                        part_number += 1
                        pbar.update(len(part_data))

            # Complete multipart upload
            response = client.complete_multipart_upload(vaultName=vault_name, uploadId=upload_id, archiveSize=str(file_size), checksum=original_checksum)
            result_obj['complete_multipart_upload'] = response
            click.echo("===========================")
            click.echo("Upload complete.")
            click.echo(json.dumps(response, indent=2))

        except Exception as e:
            # Abort multipart upload in case of error
            result_obj['abort_multipart_upload'] = abort_upload(ctx, vault_name, upload_id)
            verbose_log(ctx, result_obj['abort_multipart_upload'])
            click.echo(f"Upload aborted due to error: {str(e)}")
    finally:
        with open(log_filename, 'w') as log_file:
            log_file.write(json.dumps(result_obj, indent=2))

    click.echo(f"Response saved to {log_filename}")

@cli.command()
@click.argument('file_path')
@click.pass_context
def upload(ctx, file_path):
    """Upload a file to a Glacier vault without using multipart upload."""
    vault_name = ctx.obj['vault_name']
    if not vault_name:
        return
    file_name = os.path.basename(file_path)
    session = boto3.Session(profile_name=ctx.obj['profile'])
    client = session.client('glacier', region_name=ctx.obj['region'])
    file_size = os.path.getsize(file_path)

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    log_filename = f"{file_name}_{timestamp}_{vault_name}.log"

    result_obj = {}

    try:
        original_checksum = calculate_tree_hash(open(file_path, 'rb'))
        result_obj['original_checksum'] = original_checksum
        result_obj['file_size'] = file_size

        with open(file_path, 'rb') as f:
            file_data = f.read()

        # Upload file
        response = client.upload_archive(vaultName=vault_name, archiveDescription=file_name, body=file_data, checksum=original_checksum)
        result_obj['upload_archive'] = response
        click.echo("===========================")
        click.echo("Upload complete.")
        click.echo(json.dumps(response, indent=2))

    except Exception as e:
        result_obj['error'] = str(e)
        click.echo(f"Upload failed due to error: {str(e)}")
    finally:
        with open(log_filename, 'w') as log_file:
            log_file.write(json.dumps(result_obj, indent=2))

    click.echo(f"Response saved to {log_filename}")

@cli.command()
@click.argument('file_path')
@click.pass_context
def download(ctx, file_path):
    """Download a file from a Glacier vault."""
    vault_name = ctx.obj['vault_name']
    if not vault_name:
        return
    job_id = choose_job(ctx, 'ArchiveRetrieval')
    if not job_id:
        return
    retrieve_files_from_job(ctx, vault_name, job_id, file_path)

@cli.command()
@click.pass_context
def inventory_retrieval(ctx):
    """Initiate inventory retrieval for all archives in a Glacier vault."""
    vault_name = ctx.obj['vault_name']
    if not vault_name:
        return
    session = boto3.Session(profile_name=ctx.obj['profile'])
    client = session.client('glacier', region_name=ctx.obj['region'])
    inventory_job = client.initiate_job(
        vaultName=vault_name,
        jobParameters={
            'Type': 'inventory-retrieval'
        }
    )
    click.echo(f"Initiated inventory retrieval job for vault {vault_name}. Job ID: {inventory_job['jobId']}")
    if ctx.obj['verbose']:
        click.echo(json.dumps(inventory_job, indent=2))

@cli.command()
@click.pass_context
def vault_cleanup(ctx):
    """Delete all archives in a Glacier vault using a specific job ID."""
    vault_name = ctx.obj['vault_name']
    if not vault_name:
        return

    job_id = get_most_recent_job(ctx, 'InventoryRetrieval')
    if job_id:
        click.echo(f"Found most recent InventoryRetrieval job with ID: {job_id}")
        use_recent_job = click.confirm("Do you want to use this job?", default=True)
        if not use_recent_job:
            job_id = click.prompt("Enter job ID")
    else:
        job_id = click.prompt("Enter job ID")

    confirm_vault_name = click.prompt(f"Type the vault name '{vault_name}' to confirm cleanup")
    if confirm_vault_name != vault_name:
        click.echo("Vault name does not match. Aborting cleanup.")
        return

    session = boto3.Session(profile_name=ctx.obj['profile'])
    client = session.client('glacier', region_name=ctx.obj['region'])
    response = client.describe_job(vaultName=vault_name, jobId=job_id)
    if response['Action'] == 'InventoryRetrieval' and response['StatusCode'] == 'Succeeded':
        inventory = json.loads(response['InventoryRetrievalParameters']['Inventory'])
        for archive in inventory['ArchiveList']:
            client.delete_archive(vaultName=vault_name, archiveId=archive['ArchiveId'])
            click.echo(f"Deleted archive {archive['ArchiveId']} from vault {vault_name}")
        if ctx.obj['verbose']:
            click.echo(json.dumps(response, indent=2))
    else:
        click.echo(f"Job {job_id} is not an inventory retrieval job or has not succeeded.")

@cli.command()
@click.argument('archive_id')
@click.pass_context
def delete(ctx, archive_id):
    """Delete a file from a Glacier vault given the archive ID."""
    vault_name = ctx.obj['vault_name']
    if not vault_name:
        return
    session = boto3.Session(profile_name=ctx.obj['profile'])
    client = session.client('glacier', region_name=ctx.obj['region'])
    response = client.delete_archive(vaultName=vault_name, archiveId=archive_id)
    click.echo(json.dumps(response, indent=2))

@cli.command()
@click.argument('archive_id')
@click.pass_context
def archive_retrieval(ctx, archive_id):
    """Initiate archive retrieval for a specific archive in a Glacier vault."""
    vault_name = ctx.obj['vault_name']
    if not vault_name:
        return
    session = boto3.Session(profile_name=ctx.obj['profile'])
    client = session.client('glacier', region_name=ctx.obj['region'])
    response = client.initiate_job(
        vaultName=vault_name,
        jobParameters={
            'Type': 'archive-retrieval',
            'ArchiveId': archive_id
        }
    )
    click.echo(f"Initiated archive retrieval job for archive {archive_id} in vault {vault_name}. Job ID: {response['jobId']}")
    verbose_log(ctx, response)

@cli.command()
@click.pass_context
def ls(ctx):
    """Show files from the most recent InventoryRetrieval job from the last month."""
    vault_name = ctx.obj['vault_name']
    if not vault_name:
        return
    job_id = get_most_recent_job(ctx, 'InventoryRetrieval')
    if not job_id:
        return
    click.echo(f"Found InventoryRetrieval job with ID: {job_id}")
    retrieve_files_from_job(ctx, vault_name, job_id)

    # Save the result into a log file
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    log_filename = f"{ctx.obj['region']}-{vault_name}-files-{timestamp}.log"
    with open(log_filename, 'w') as log_file:
        session = boto3.Session(profile_name=ctx.obj['profile'])
        client = session.client('glacier', region_name=ctx.obj['region'])
        response = client.get_job_output(vaultName=vault_name, jobId=job_id)
        inventory = json.loads(response['body'].read())
        log_file.write(json.dumps(inventory, indent=2))
        for archive in inventory['ArchiveList']:
            click.echo(f"Archive ID: {archive['ArchiveId']}, Size: {archive['Size']}, Description: {archive.get('ArchiveDescription', 'N/A')}")
    click.echo(f"Response saved to {log_filename}")

def choose_job(ctx, job_type):
    """Prompt the user to choose a job of a specific type from the last month."""
    vault_name = ctx.obj['vault_name']
    session = boto3.Session(profile_name=ctx.obj['profile'])
    client = session.client('glacier', region_name=ctx.obj['region'])
    one_month_ago = datetime.now() - timedelta(days=30)
    response = client.list_jobs(vaultName=vault_name)
    verbose_log(ctx, response)
    jobs = [
        job for job in response['JobList']
        if job['Action'] == job_type and datetime.strptime(job['CreationDate'], '%Y-%m-%dT%H:%M:%S.%fZ') > one_month_ago
    ]

    if not jobs:
        click.echo(f"No {job_type} jobs found in the last month.")
        return None

    click.echo(f"Select a {job_type} job:")
    for i, job in enumerate(jobs):
        click.echo(f"{i + 1}. Job ID: {job['JobId']}, Creation Date: {job['CreationDate']}, Status: {job['StatusCode']}")

    choice = click.prompt("Enter the number of the job you want to select", type=int)
    if 1 <= choice <= len(jobs):
        return jobs[choice - 1]['JobId']
    else:
        click.echo("Invalid choice.")
        return None

def get_most_recent_job(ctx, job_type):
    """Get the most recent job of a specific type from the last month."""
    vault_name = ctx.obj['vault_name']
    session = boto3.Session(profile_name=ctx.obj['profile'])
    client = session.client('glacier', region_name=ctx.obj['region'])
    one_month_ago = datetime.now() - timedelta(days=30)
    response = client.list_jobs(vaultName=vault_name)
    verbose_log(ctx, response)
    jobs = [
        job for job in response['JobList']
        if job['Action'] == job_type and datetime.strptime(job['CreationDate'], '%Y-%m-%dT%H:%M:%S.%fZ') > one_month_ago
    ]

    if not jobs:
        click.echo(f"No {job_type} jobs found in the last month.")
        return None

    most_recent_job = max(jobs, key=lambda job: job['CreationDate'])
    return most_recent_job['JobId']

def retrieve_files_from_job(ctx, vault_name, job_id, file_path=None):
    """Retrieve files from a selected job."""
    session = boto3.Session(profile_name=ctx.obj['profile'])
    client = session.client('glacier', region_name=ctx.obj['region'])
    response = client.get_job_output(vaultName=vault_name, jobId=job_id)
    verbose_log(ctx, response)
    if file_path:
        with open(file_path, 'wb') as f:
            f.write(response['body'].read())
        click.echo(f"Downloaded to {file_path}")
    else:
        inventory = json.loads(response['body'].read())
        for archive in inventory['ArchiveList']:
            click.echo(f"Archive ID: {archive['ArchiveId']}, Size: {archive['Size']}, Description: {archive.get('ArchiveDescription', 'N/A')}")

if __name__ == '__main__':
    cli(obj={})
    click.echo("Goodbye!")
