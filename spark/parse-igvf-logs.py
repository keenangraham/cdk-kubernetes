import os

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, regexp_extract


def main():
    spark = SparkSession.builder \
        .appName("S3 Log Reader") \
        .getOrCreate()

    log_regex_pattern = r'([^ ]*) ([^ ]*) \[(.*?)\] ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ("[^"]+"|-) (\d+|-|-) ([^ ]*) (\d+|-|-) (\d+|-|-) (\d+|-|-) (\d+|-|-) ("[^"]*"|-) ("[^"]*"|-) ([^ ]*)'

    date = os.environ['DATE']
    print("*****************")
    print('DATE IS:' + date)
    print("*****************")
    df = spark.read.text(f's3a://igvf-public-logs/{date}*')

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
    output_path = f's3a://igvf-parsed-logs/parquet/date={date}'
    parsed_df.repartition(1).write.mode('overwrite').parquet(output_path)


if __name__ == "__main__":
    main()
