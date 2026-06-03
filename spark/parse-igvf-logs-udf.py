import os
import re

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, udf
from pyspark.sql.types import StructType, StructField, StringType


LOG_FIELDS = [
    'bucket_owner', 'bucket_name', 'timestamp', 'remote_ip', 'requester',
    'request_id', 'operation', 'key', 'request_uri', 'http_status',
    'error_code', 'bytes_sent', 'object_size', 'total_time',
    'turn_around_time', 'referrer', 'user_agent', 'version_id',
]

LOG_SCHEMA = StructType([StructField(f, StringType()) for f in LOG_FIELDS])

LOG_PATTERN = re.compile(
    r'([^ ]*) ([^ ]*) \[(.*?)\] ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ("[^"]+"|-) (\d+|-|-) ([^ ]*) (\d+|-|-) (\d+|-|-) (\d+|-|-) (\d+|-|-) ("[^"]*"|-) ("[^"]*"|-) ([^ ]*)'
)


@udf(returnType=LOG_SCHEMA)
def parse_log_line(line):
    m = LOG_PATTERN.match(line)
    if m:
        return m.groups()
    return tuple([None] * len(LOG_FIELDS))


def main():
    spark = SparkSession.builder \
        .appName("S3 Log Reader") \
        .getOrCreate()

    date = os.environ['DATE']
    print(f'DATE IS: {date}')

    df = spark.read.text(f's3a://igvf-public-logs/{date}*')

    parsed_df = df.select(parse_log_line(col('value')).alias('parsed')) \
                  .select('parsed.*')

    output_path = f's3a://igvf-parsed-logs/parquet/date={date}'
    parsed_df.repartition(10).write.mode('overwrite').parquet(output_path)


if __name__ == "__main__":
    main()
