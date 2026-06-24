import os
import boto3

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, regexp_extract


def get_s3a_paths(s3_client, bucket: str, prefix: str) -> list:
    s3a_paths = []
    continuation_token = None

    while True:
        list_kwargs = {'Bucket': bucket, 'Prefix': prefix}
        if continuation_token:
            list_kwargs['ContinuationToken'] = continuation_token

        response = s3_client.list_objects_v2(**list_kwargs)

        if 'Contents' in response:
            for obj in response['Contents']:
                s3a_paths.append(f"s3a://{bucket}/{obj['Key']}")

        if response.get('NextContinuationToken'):
            continuation_token = response['NextContinuationToken']
        else:
            break

    return s3a_paths


def main():
    spark = SparkSession.builder \
        .appName("S3 Encode Log Reader") \
        .config("spark.hadoop.mapreduce.input.fileinputformat.split.minsize", "134217728") \
        .config("spark.hadoop.mapreduce.input.fileinputformat.split.maxsize", "268435456") \
        .getOrCreate()

    log_regex_pattern = r'([^ ]*) ([^ ]*) \[(.*?)\] ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ("[^"]+"|-) (\d+|-|-) ([^ ]*) (\d+|-|-) (\d+|-|-) (\d+|-|-) (\d+|-|-) ("[^"]*"|-) ("[^"]*"|-) ([^ ]*)'

    session = boto3.Session(
        aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
    )
    s3_client = session.client('s3')

    date = os.environ['DATE']
    print("*****************")
    print('DATE IS:' + date)
    print("*****************")

    files_to_read = get_s3a_paths(s3_client, 'encode-public-logs', date)
    df = spark.read.text(files_to_read)

    parsed_df = df.select(
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
        regexp_extract(col('value'), log_regex_pattern, 18).alias('version_id'),
    )
    output_path = f's3a://encode-parsed-logs/parquet/date={date}'
    parsed_df.repartition(10).write.mode('overwrite').parquet(output_path)


if __name__ == "__main__":
    main()
