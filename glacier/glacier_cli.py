import boto3
import click
import json
from tqdm import tqdm
import os
import hashlib
from botocore.utils import calculate_tree_hash
from datetime import datetime

@click.group()
@click.option('--region', default='us-east-1', help='AWS region')
@click.pass_context
def cli(ctx, region):
    """A CLI to interact with AWS S3 Glacier."""
    ctx.ensure_object(dict)
    ctx.obj['region'] = region

@cli.command()
@click.pass_context
def list_vaults(ctx):
    """List all Glacier vaults."""
    client = boto3.client('glacier', region_name=ctx.obj['region'])
    response = client.list_vaults()
    for vault in response.get('VaultList', []):
        click.echo("========  Vaults  ========")
        click.echo(f"Name: {vault['VaultName']}")
        click.echo(f"Arn: {vault['VaultARN']}")
        click.echo("--------------------")

@cli.command()
@click.argument('vault_name')
@click.pass_context
def list_jobs(ctx, vault_name):
    """List jobs in a Glacier vault."""
    client = boto3.client('glacier', region_name=ctx.obj['region'])
    response = client.list_jobs(vaultName=vault_name)
    click.echo(json.dumps(response, indent=2))

@cli.command()
@click.argument('vault_name')
@click.argument('upload_id')
@click.pass_context
def abort_upload(ctx, vault_name, upload_id):
    """Abort a multipart upload in a Glacier vault."""
    client = boto3.client('glacier', region_name=ctx.obj['region'])
    response = client.abort_multipart_upload(vaultName=vault_name, uploadId=upload_id)
    click.echo(json.dumps(response, indent=2))
    return response

@cli.command()
@click.argument('vault_name')
@click.argument('file_path')
@click.pass_context
def upload_multipart(ctx, vault_name, file_path):
    """Upload a file to a Glacier vault using multipart upload."""
    file_name = os.path.basename(file_path)
    client = boto3.client('glacier', region_name=ctx.obj['region'])
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
                        result_obj[f'part_{part_number}'] = response
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
            click.echo(f"Upload aborted due to error: {str(e)}")
    finally:
        with open(log_filename, 'w') as log_file:
            log_file.write(json.dumps(result_obj, indent=2))

    click.echo(f"Response saved to {log_filename}")

@cli.command()
@click.argument('vault_name')
@click.argument('file_path')
@click.pass_context
def upload(ctx, vault_name, file_path):
    """Upload a file to a Glacier vault without using multipart upload."""
    file_name = os.path.basename(file_path)
    client = boto3.client('glacier', region_name=ctx.obj['region'])
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
@click.argument('vault_name')
@click.argument('job_id')
@click.argument('file_path')
@click.pass_context
def download(ctx, vault_name, job_id, file_path):
    """Download a file from a Glacier vault."""
    client = boto3.client('glacier', region_name=ctx.obj['region'])
    response = client.get_job_output(vaultName=vault_name, jobId=job_id)
    with open(file_path, 'wb') as f:
        f.write(response['body'].read())
    click.echo(f"Downloaded to {file_path}")

@cli.command()
@click.argument('vault_name')
@click.pass_context
def retrieve_archives(ctx, vault_name):
    """Initiate archive retrieval for all archives in a Glacier vault."""
    client = boto3.client('glacier', region_name=ctx.obj['region'])
    response = client.list_vaults()
    for vault in response.get('VaultList', []):
        if vault['VaultName'] == vault_name:
            inventory_job = client.initiate_job(
                vaultName=vault_name,
                jobParameters={
                    'Type': 'inventory-retrieval'
                }
            )
            click.echo(f"Initiated inventory retrieval job for vault {vault_name}. Job ID: {inventory_job['jobId']}")
            return
    click.echo(f"Vault {vault_name} not found.")

@cli.command()
@click.argument('vault_name')
@click.argument('job_id')
@click.pass_context
def empty_vault(ctx, vault_name, job_id):
    """Delete all archives in a Glacier vault using a specific job ID."""
    client = boto3.client('glacier', region_name=ctx.obj['region'])
    response = client.describe_job(vaultName=vault_name, jobId=job_id)
    if response['Action'] == 'InventoryRetrieval' and response['StatusCode'] == 'Succeeded':
        inventory = json.loads(response['InventoryRetrievalParameters']['Inventory'])
        for archive in inventory['ArchiveList']:
            client.delete_archive(vaultName=vault_name, archiveId=archive['ArchiveId'])
            click.echo(f"Deleted archive {archive['ArchiveId']} from vault {vault_name}")
    else:
        click.echo(f"Job {job_id} is not an inventory retrieval job or has not succeeded.")

@cli.command()
@click.argument('vault_name')
@click.argument('archive_id')
@click.pass_context
def delete_file(ctx, vault_name, archive_id):
    """Delete a file from a Glacier vault given the archive ID."""
    client = boto3.client('glacier', region_name=ctx.obj['region'])
    response = client.delete_archive(vaultName=vault_name, archiveId=archive_id)
    click.echo(json.dumps(response, indent=2))

if __name__ == '__main__':
    cli(obj={})
