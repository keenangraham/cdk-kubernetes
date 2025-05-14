import os
import boto3

from pyspark.sql import SparkSession
from pyspark.sql import Row
from pyspark.sql.functions import col, regexp_extract

def get_s3a_paths(s3_client, bucket: str, prefix: str) -> list:
    """
    Returns list of s3a:// paths for all objects in an S3 bucket/prefix
    Handles pagination automatically for >1000 objects
    
    Args:
        s3_client: Configured boto3 S3 client
        bucket: S3 bucket name
        prefix: Prefix path to search under (can be empty string)
    
    Returns:
        List of s3a:// paths (e.g. ["s3a://bucket/path/to/object1", ...])
    """
    s3a_paths = []
    continuation_token = None
    
    while True:
        # Configure request parameters
        list_kwargs = {
            'Bucket': bucket,
            'Prefix': prefix
        }
        if continuation_token:
            list_kwargs['ContinuationToken'] = continuation_token

        # Get object page
        response = s3_client.list_objects_v2(**list_kwargs)
        
        # Process objects if any were returned
        if 'Contents' in response:
            for obj in response['Contents']:
                # Format as s3a:// path
                s3a_path = f"s3a://{bucket}/{obj['Key']}"
                s3a_paths.append(s3a_path)

        # Check if more pages exist
        if response.get('NextContinuationToken'):
            continuation_token = response['NextContinuationToken']
        else:
            break

    return s3a_paths

def main():
    spark = SparkSession.builder \
    .appName("S3 Log Reader") \
    .config("spark.hadoop.mapreduce.input.fileinputformat.split.minsize", "134217728")  \
    .config("spark.hadoop.mapreduce.input.fileinputformat.split.maxsize", "268435456")  \
    .getOrCreate()

    log_regex_pattern = r'([^ ]*) ([^ ]*) \[(.*?)\] ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ("[^"]+"|-) (\d+|-|-) ([^ ]*) (\d+|-|-) (\d+|-|-) (\d+|-|-) (\d+|-|-) ("[^"]*"|-) ("[^"]*"|-) ([^ ]*)'

    session = boto3.Session(aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'], aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'])
    s3_client = session.client('s3')
    date = os.environ['DATE']
    print("*****************")
    print('DATE IS:' + date)
    print("*****************")
    files_to_read = get_s3a_paths(s3_client, 'encode-public-logs', date)
    df = spark.read.text(files_to_read)
    print('Number of logs', df.count())

    parsed_df = df.select(
    'value',
    regexp_extract(col('value'), log_regex_pattern, 1).alias('bucket_owner'),
    regexp_extract(col('value'), log_regex_pattern, 2).alias('bucket_name'),
    regexp_extract(col('value'), log_regex_pattern, 3).alias('timestamp'),
    regexp_extract(col('value'), log_regex_pattern, 4).alias('remote_ip'),
    regexp_extract(col('value'), log_regex_pattern, 5).alias('requester'),
    regexp_extract(col('value'), log_regex_pattern, 6).alias('request_id'),
    regexp_extract(col('value'), log_regex_pattern, 7).alias('operation'),
    regexp_extract(col('value'), log_regex_pattern, 8).alias('key'),
    regexp_extract(col('value'), log_regex_pattern, 9).alias('request_uri'),
    regexp_extract(col('value'), log_regex_pattern, 10).alias('http_status'),
    regexp_extract(col('value'), log_regex_pattern, 11).alias('error_code'),
    regexp_extract(col('value'), log_regex_pattern, 12).alias('bytes_sent'),
    regexp_extract(col('value'), log_regex_pattern, 13).alias('object_size'),
    regexp_extract(col('value'), log_regex_pattern, 14).alias('total_time'),
    regexp_extract(col('value'), log_regex_pattern, 15).alias('turn_around_time'),
    regexp_extract(col('value'), log_regex_pattern, 16).alias('referrer'),
    regexp_extract(col('value'), log_regex_pattern, 17).alias('user_agent'),
    regexp_extract(col('value'), log_regex_pattern, 18).alias('version_id')
    )
    output_path = f's3a://spark-log-parsing-test/encode-logs/{date}'
    parsed_df.repartition(30).write.mode('overwrite').parquet(output_path)


if __name__ == "__main__":
    main()
