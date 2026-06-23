import clickhouse_connect
import os
import sys

date = sys.argv[1]
aws_key = os.environ['AWS_ACCESS_KEY_ID']
aws_secret = os.environ['AWS_SECRET_ACCESS_KEY']
ch_password = os.environ['CLICKHOUSE_PASSWORD']
ch_host = os.environ['CLICKHOUSE_HOST']

client = clickhouse_connect.get_client(
    host=ch_host,
    port=8123,
    username='default',
    password=ch_password,
)

client.command('CREATE DATABASE IF NOT EXISTS encode_logs')

client.command('''
    CREATE TABLE IF NOT EXISTS encode_logs.s3_access_logs (
        bucket_owner     String,
        bucket_name      String,
        timestamp        String,
        remote_ip        String,
        requester        String,
        request_id       String,
        operation        String,
        key              String,
        request_uri      String,
        http_status      String,
        error_code       String,
        bytes_sent       String,
        object_size      String,
        total_time       String,
        turn_around_time String,
        referrer         String,
        user_agent       String,
        version_id       String,
        date             Date
    )
    ENGINE = MergeTree()
    PARTITION BY date
    ORDER BY (date, request_id)
''')

print(f'[{date}] Dropping partition')
try:
    client.command(f"ALTER TABLE encode_logs.s3_access_logs DROP PARTITION '{date}'")
except Exception:
    pass

print(f'[{date}] Inserting from s3://encode-parsed-logs/parquet/date={date}/')
client.command(f'''
    INSERT INTO encode_logs.s3_access_logs
    SELECT
        bucket_owner, bucket_name, timestamp, remote_ip, requester,
        request_id, operation, key, request_uri, http_status, error_code,
        bytes_sent, object_size, total_time, turn_around_time, referrer,
        user_agent, version_id,
        toDate('{date}')
    FROM s3(
        's3://encode-parsed-logs/parquet/date={date}/*.parquet',
        '{aws_key}', '{aws_secret}',
        'Parquet'
    )
''')

row_count = client.query(
    f"SELECT count() FROM encode_logs.s3_access_logs WHERE date = '{date}'"
).first_row[0]
print(f'[{date}] Loaded {row_count:,} rows')
